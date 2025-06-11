from constant.constant import data
from fastapi.encoders import jsonable_encoder
import json, uuid
from typing import List
from sqlalchemy.orm import Session
from fastapi import FastAPI, WebSocket, Depends, Response, HTTPException, Request, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database.database import get_db
from utils.utils import Generator as gen, DbQuickActions as dbQuick, Cookie as cook
from schema.schema import ChessAction, UserSchema, GuestSchema
from model.model import User, Guest, GuestSession, OfflineGameSession, GuestsGameOfflineSession
import asyncio
import uvicorn
import os

origins = [os.getenv("BASE_URL")]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # ou ["*"] pour tout autoriser (pas conseillé en prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
active_connections = set()

#get all the users
@app.get("/users/", response_model=List[UserSchema])
def read_users(db: Session = Depends(get_db)):  
    users = db.query(User).all()  # Récupérer tous les utilisateurs
    return users


#create a new guest player
@app.post("/guest/", response_model=GuestSchema)
async def create_guest(response: Response,  db: Session = Depends(get_db)):
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
    cook.send_cookie_for_guest(response,"guest_session",sessionId)
    cook.send_cookie_for_guest(response,"guest_id",guest.id)

    return guest


#create a game session with a shared link
@app.post("/guest/gamesession")
async def create_offline_game_session(request: Request, db: Session = Depends(get_db)):
    #check if the player is a guest
    guestId = request.cookies.get('guest_id')
    if not guestId:
        raise HTTPException(status_code=400)
    
    #Creation of a game
    offlineGameSession = OfflineGameSession(
        data=jsonable_encoder(data)
    )
    dbQuick.add_object_in_db(db, offlineGameSession)

    #id used to create a link to share with an other player
    return {"game_session": offlineGameSession.id}


#join a game session as a invited player
@app.post("/guest/gamesession/join/{gameSessionId}")
async def join_offline_game_session(request: Request, gameSessionId: str, db: Session = Depends(get_db)):

    #check if the player is a guest
    guestId = request.cookies.get('guest_id')
    if not guestId:
        raise HTTPException(status_code=400)

    #check if the session you're tring to join exists
    offlineGameSessionExists = db.query(OfflineGameSession).filter(OfflineGameSession.id == gameSessionId).first()
    if offlineGameSessionExists is None:
        raise HTTPException(status_code=404)
    
    testGuestsOfflineSession = db.query(GuestsGameOfflineSession).filter(
        GuestsGameOfflineSession.offline_game_session_id == gameSessionId
    )
    #check if the session is already full or not
    if testGuestsOfflineSession.count() >= 2:
        raise HTTPException(status_code=403)
    
    #check if the player is already in the session
    currentPlayerIsInGuestsOfflineSession = testGuestsOfflineSession.filter(
        GuestsGameOfflineSession.guest_id == guestId
    ).first()
    if currentPlayerIsInGuestsOfflineSession is not None:
        raise HTTPException(status_code=403) 
    
    #add the player in the offline game session
    guestsOfflineSession = GuestsGameOfflineSession(
        offline_game_session_id=gameSessionId,
        guest_id=guestId
    )
    dbQuick.add_object_in_db(db, guestsOfflineSession)

    return {"message": f"Joined game session with ID: {gameSessionId}"}

        
@app.websocket("/ws/chess/{gameSessionId}")
async def websocket_endpoint(websocket: WebSocket , gameSessionId: str, db: Session = Depends(get_db)):
    await websocket.accept()
    active_connections.add(websocket)

    try:
        #Test if the uuid format is correct
        try:
            uuid.UUID(gameSessionId)
        except ValueError:
            await websocket.close(code=403)
            return
        
        while True:
            #check if the player is a guest
            guestId = websocket.cookies.get('guest_id')
            print("cookie",guestId)

            gameSession = db.query(GuestsGameOfflineSession).filter(GuestsGameOfflineSession.offline_game_session_id == gameSessionId)
            #if the session doesn't exists close the websocket
            if gameSession is None:
                await websocket.send_text(json.dumps({"response": "Session not found"}))
                await websocket.close(code=404)
                return
    
            #wait a player if you're alone
            if gameSession.count() == 2:
                break
            await websocket.send_text(json.dumps(jsonable_encoder({"response": "Waiting for a player"})))
            await asyncio.sleep(2)

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

    except WebSocketDisconnect as e:
        print(f"Client disconnected: {e}")
        active_connections.remove(websocket)
    except Exception as e:
        print(f"Client disconnected: {e}")