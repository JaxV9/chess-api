from .constant.constant import data
from fastapi.encoders import jsonable_encoder
import json
from .schema.schema import ChessAction, UserSchema
from typing import List
from sqlalchemy.orm import Session
from fastapi import FastAPI, WebSocket, Depends
from .database.database import get_db
from .model.model import User

app = FastAPI()
active_connections = set()

@app.get("/users/", response_model=List[UserSchema])
def read_users(db: Session = Depends(get_db)):  
    users = db.query(User).all()  # Récupérer tous les utilisateurs
    return users

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
                for connection in active_connections:
                    await connection.send_text(json.dumps(jsonable_encoder(response)))

    except Exception as e:
        print(f"Client disconnected: {e}")