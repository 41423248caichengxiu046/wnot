from waitress import serve
from app import app  # 假設你的 Flask 應用定義在 app.py 中，並且 `app` 是你的 Flask 應用實例

if __name__ == "__main__":
    # 使用 8 個執行緒來啟動應用
    serve(app, host='127.0.0.1', port=8499, threads=8)