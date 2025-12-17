# py/robot_lib_websocket.py
from browser import document, html, timer, bind, websocket
import json

# 每個格子的像素大小
CELL_SIZE = 40

# 牆壁厚度，用於圖片位置調整
WALL_THICKNESS = 6

# 牆壁與機器人圖片的來源路徑
IMG_PATH = "https://mde.tw/cp2025/reeborg/src/images/"

# --- 定義世界地圖的類別 ---
class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.layers = self._create_layers()
        self._init_html()
        self._draw_grid()
        self._draw_walls()

    def _create_layers(self):
        return {
            "grid": html.CANVAS(width=self.width * CELL_SIZE, height=self.height * CELL_SIZE),
            "walls": html.CANVAS(width=self.width * CELL_SIZE, height=self.height * CELL_SIZE),
            "objects": html.CANVAS(width=self.width * CELL_SIZE, height=self.height * CELL_SIZE),
            "robots": html.CANVAS(width=self.width * CELL_SIZE, height=self.height * CELL_SIZE),
        }

    def _init_html(self):
        container = html.DIV(style={
            "position": "relative",
            "width": f"{self.width * CELL_SIZE}px",
            "height": f"{self.height * CELL_SIZE}px"
        })
        for z, canvas in enumerate(self.layers.values()):
            canvas.style = {
                "position": "absolute",
                "top": "0px",
                "left": "0px",
                "zIndex": str(z)
            }
            container <= canvas

        button_container = html.DIV(style={"margin-top": "10px", "text-align": "center"})
        move_button = html.BUTTON("Move Forward (j)", id="move_button")
        turn_button = html.BUTTON("Turn Left (i)", id="turn_button")
        button_container <= move_button
        button_container <= turn_button

        document["brython_div1"].clear()
        document["brython_div1"] <= container
        document["brython_div1"] <= button_container

    def _draw_grid(self):
        ctx = self.layers["grid"].getContext("2d")
        ctx.strokeStyle = "#cccccc"
        for i in range(self.width + 1):
            ctx.beginPath()
            ctx.moveTo(i * CELL_SIZE, 0)
            ctx.lineTo(i * CELL_SIZE, self.height * CELL_SIZE)
            ctx.stroke()
        for j in range(self.height + 1):
            ctx.beginPath()
            ctx.moveTo(0, j * CELL_SIZE)
            ctx.lineTo(self.width * CELL_SIZE, j * CELL_SIZE)
            ctx.stroke()

    def _draw_image(self, ctx, src, x, y, w, h, offset_x=0, offset_y=0):
        img = html.IMG()
        img.src = src
        def onload(evt):
            px = x * CELL_SIZE + offset_x
            py = (self.height - 1 - y) * CELL_SIZE + offset_y
            ctx.drawImage(img, px, py, w, h)
        img.bind("load", onload)

    def _draw_walls(self):
        ctx = self.layers["walls"].getContext("2d")
        for x in range(self.width):
            self._draw_image(ctx, IMG_PATH + "north.png", x, self.height - 1, CELL_SIZE, WALL_THICKNESS)
            self._draw_image(ctx, IMG_PATH + "north.png", x, 0, CELL_SIZE, WALL_THICKNESS, offset_y=CELL_SIZE - WALL_THICKNESS)
        for y in range(self.height):
            self._draw_image(ctx, IMG_PATH + "east.png", 0, y, WALL_THICKNESS, CELL_SIZE)
            self._draw_image(ctx, IMG_PATH + "east.png", self.width - 1, y, WALL_THICKNESS, CELL_SIZE, offset_x=CELL_SIZE - WALL_THICKNESS)

    def robot(self, x, y):
        ctx = self.layers["robots"].getContext("2d")
        self._draw_image(ctx, IMG_PATH + "blue_robot_e.png", x - 1, y - 1, CELL_SIZE, CELL_SIZE)

# --- 定義動畫機器人類別 ---
class AnimatedRobot:
    def __init__(self, world, x, y):
        self.world = world
        self.x = x - 1
        self.y = y - 1
        self.facing = "E"
        self.facing_order = ["E", "N", "W", "S"]
        self.robot_ctx = world.layers["robots"].getContext("2d")
        self.trace_ctx = world.layers["objects"].getContext("2d")
        self.queue = []
        self.running = False
        self.images = {}
        for direction in self.facing_order:
            img = html.IMG()
            img.src = IMG_PATH + f"blue_robot_{direction.lower()}.png"
            self.images[direction] = img
        self._draw_robot()
        # 加入 WebSocket 連線（使用 IPv6 地址）
        self.ws = websocket.WebSocket("ws://[<主機IPv6地址>]:8765")  # 替換為主機 IPv6 地址
        self.ws.bind("open", lambda evt: print("WebSocket 連線已建立"))
        self.ws.bind("message", self.on_message)
        self.ws.bind("error", lambda evt: print("WebSocket 錯誤:", evt))

    def on_message(self, evt):
        data = json.loads(evt.data)
        command = data.get("command")
        print(f"收到 WebSocket 指令: {command}")
        if command == "move":
            self.move(1)
        elif command == "turn_left":
            self.turn_left()

    def _robot_image(self):
        return {
            "E": "blue_robot_e.png",
            "N": "blue_robot_n.png",
            "W": "blue_robot_w.png",
            "S": "blue_robot_s.png"
        }[self.facing]

    def _draw_robot(self):
        self.robot_ctx.clearRect(0, 0, self.world.width * CELL_SIZE, self.world.height * CELL_SIZE)
        img = self.images[self.facing]
        px = self.x * CELL_SIZE
        py = (self.world.height - 1 - self.y) * CELL_SIZE
        if img.complete:
            self.robot_ctx.drawImage(img, px, py, CELL_SIZE, CELL_SIZE)
        else:
            def onload(evt):
                self.robot_ctx.drawImage(img, px, py, CELL_SIZE, CELL_SIZE)
            img.bind("load", onload)

    def _draw_trace(self, from_x, from_y, to_x, to_y):
        ctx = self.trace_ctx
        ctx.strokeStyle = "#d33"
        ctx.lineWidth = 2
        ctx.beginPath()
        fx = from_x * CELL_SIZE + CELL_SIZE / 2
        fy = (self.world.height - 1 - from_y) * CELL_SIZE + CELL_SIZE / 2
        tx = to_x * CELL_SIZE + CELL_SIZE / 2
        ty = (self.world.height - 1 - to_y) * CELL_SIZE + CELL_SIZE / 2
        ctx.moveTo(fx, fy)
        ctx.lineTo(tx, ty)
        ctx.stroke()

    def move(self, steps):
        def action(next_done):
            def step():
                nonlocal steps
                if steps == 0:
                    next_done()
                    return
                from_x, from_y = self.x, self.y
                dx, dy = 0, 0
                if self.facing == "E": dx = 1
                elif self.facing == "W": dx = -1
                elif self.facing == "N": dy = 1
                elif self.facing == "S": dy = -1
                next_x = self.x + dx
                next_y = self.y + dy
                if 0 <= next_x < self.world.width and 0 <= next_y < self.world.height:
                    self.x, self.y = next_x, next_y
                    self._draw_trace(from_x, from_y, self.x, self.y)
                    self._draw_robot()
                    steps -= 1
                    timer.set_timeout(step, 200)
                else:
                    print("已經撞牆，停止移動！")
                    next_done()
            step()
        self.queue.append(action)
        self._run_queue()

    def turn_left(self):
        def action(done):
            idx = self.facing_order.index(self.facing)
            self.facing = self.facing_order[(idx + 1) % 4]
            self._draw_robot()
            timer.set_timeout(done, 300)
        self.queue.append(action)
        self._run_queue()

    def _run_queue(self):
        if self.running or not self.queue:
            return
        self.running = True
        action = self.queue.pop(0)
        action(lambda: self._done())

    def _done(self):
        self.running = False
        self._run_queue()

# --- 主程式 ---
w = World(10, 10)
w.robot(1, 1)
r = AnimatedRobot(w, 1, 1)

# 綁定鍵盤控制
@bind(document, "keydown")
def keydown(evt):
    if evt.key == "j":
        r.move(1)
    elif evt.key == "i":
        r.turn_left()

# 綁定按鈕控制
@bind(document["move_button"], "click")
def move_click(evt):
    r.move(1)

@bind(document["turn_button"], "click")
def turn_click(evt):
    r.turn_left()