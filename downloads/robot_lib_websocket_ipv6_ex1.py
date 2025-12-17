from robot_lib_websocket_ipv6 import World, AnimatedRobot

# 建立世界
w = World(10, 10)
# 初始化機器人
robot = AnimatedRobot(w, 1, 1)

robot.move(1)