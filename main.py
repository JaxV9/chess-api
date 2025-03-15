from .constant.constant import data
from fastapi.encoders import jsonable_encoder
import json, uuid
from typing import List
from sqlalchemy.orm import Session
from fastapi import FastAPI, WebSocket, Depends, Response
from .database.database import get_db
from .utils.utils import Generator as gen, DbQuickActions as dbQuick, Cookie as cook
from .schema.schema import ChessAction, UserSchema, GuestSchema
from .model.model import User, Guest, GuestSession

app = FastAPI()
active_connections = set()

#get all the users
@app.get("/users/", response_model=List[UserSchema])
def read_users(db: Session = Depends(get_db)):  
    users = db.query(User).all()  # Récupérer tous les utilisateurs
    return users

#create a new guest player
@app.post("/guest/", response_model=GuestSchema)
def create_guest(response: Response, db: Session = Depends(get_db)):
    #creation of a guest
    guest = Guest(
        id=uuid.uuid4(),
        username=gen.guest_name()
    )
    dbQuick.add_object_in_db(db, guest)

    #Save the temp session of the guest and send a cookie
    sessionId = gen.guest_session_id()
    guestSession = GuestSession(
        value=sessionId,
        guest_id=guest.id
    )
    dbQuick.add_object_in_db(db, guestSession)
    cook.send_cookie_for_guest(response,sessionId)

    return guest

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