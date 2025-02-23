from .constant import data
from fastapi.encoders import jsonable_encoder
import json
from .model import ChessAction

from fastapi import FastAPI, WebSocket

app = FastAPI()
active_connections = set()

@app.websocket("/ws/chess")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            response = {"response": "ok", "data": data}
            await websocket.send_text(json.dumps(jsonable_encoder(response)))

            #wait a message from client
            message = await websocket.receive_text()
            print(f"Message reçu : {message}")

            chessAction = ChessAction.model_validate_json(message)

            if chessAction.action == "move":
                for piece in chessAction.pieces:
                    for data_piece in data:
                        if data_piece.id == piece.id:
                            data_piece.pos = piece.pos
                            break

                # Send updated data to all clients
                response = {"response": "updated", "data": data}
                for connection in active_connections:
                    await connection.send_text(json.dumps(jsonable_encoder(response)))

    except Exception as e:
        print(f"Client disconnected: {e}")