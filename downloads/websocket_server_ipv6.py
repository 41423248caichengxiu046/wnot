# websocket_server.py
import asyncio
import websockets
import json

# 儲存所有連線的客戶端
connected_clients = set()

async def handle_connection(websocket, path=None):  # path is optional
    print("客戶端已連線")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            command = data.get("command")
            print(f"收到指令: {command}")
            # 廣播指令給所有連線的客戶端（包括 Brython 客戶端）
            for client in connected_clients:
                await client.send(json.dumps({"command": command}))
    except websockets.exceptions.ConnectionClosed:
        print("客戶端斷線")
    finally:
        connected_clients.remove(websocket)

async def main():
    server = await websockets.serve(handle_connection, "::", 8765)  # Bind to IPv6 wildcard
    print("WebSocket 伺服器運行於 ws://[::]:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())