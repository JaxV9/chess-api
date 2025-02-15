from .constant import data
from fastapi.encoders import jsonable_encoder
import json

from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws/chess")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            response = {"response": "ok", "data": data}
            await websocket.send_text(json.dumps(jsonable_encoder(response)))
    except Exception as e:
        print(f"Client disconnected: {e}")