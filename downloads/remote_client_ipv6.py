# remote_client.py
import asyncio
import websockets
import json
import keyboard
import time

async def send_command(command):
    uri = "ws://[<主機IPv6地址>]:8765"  # 替換為主機 IPv6 地址
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"command": command}))
        print(f"已發送指令: {command}")

async def main():
    print("按 'j' 前進，按 'i' 左轉，按 'q' 退出")
    while True:
        if keyboard.is_pressed("q"):
            break
        if keyboard.is_pressed("j"):
            await send_command("move")
            await asyncio.sleep(0.3)  # 避免連續觸發
        if keyboard.is_pressed("i"):
            await send_command("turn_left")
            await asyncio.sleep(0.3)  # 避免連續觸發

if __name__ == "__main__":
    asyncio.run(main())