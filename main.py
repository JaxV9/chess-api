from constant.constant import data
from fastapi.encoders import jsonable_encoder
import json, uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import FastAPI, WebSocket, Depends, Response, HTTPException, Request, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database.database import get_db
from utils.utils import Generator as gen, DbQuickActions as dbQuick, Cookie as cook
from schema.schema import ChessAction, UserSchema, GuestSchema
from model.model import User, Guest, GuestSession, GameSession
import asyncio
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
@app.get("/users", response_model=List[UserSchema])
async def read_users(db: AsyncSession = Depends(get_db)):  
    result = await db.execute(select(User))
    return result.scalars().all()


#create a new guest player
@app.post("/guest", response_model=GuestSchema)
async def create_guest(response: Response, db: AsyncSession = Depends(get_db)):
    #creation of a guest — capture values before commit expires ORM attributes
    guest_id = uuid.uuid4()
    guest_username = gen.guest_name()
    guest = Guest(
        id=guest_id,
        username=guest_username
    )
    await dbQuick.add_object_in_db(db, guest)

    #Save the temp session of the guest and send a cookie
    sessionId = gen.guest_session_id()
    guestSession = GuestSession(
        value=sessionId,
        guest_id=guest_id
    )
    await dbQuick.add_object_in_db(db, guestSession)
    cook.send_cookie_for_guest(response, "guest_session", sessionId)
    cook.send_cookie_for_guest(response, "guest_id", guest_id)

    return {"id": guest_id, "username": guest_username}

@app.get("/guest", response_model=GuestSchema)
async def get_guest(request: Request, db: AsyncSession = Depends(get_db)):
    guestId = request.cookies.get('guest_id')

    if not guestId:
        raise HTTPException(status_code=401, detail="Not authenticated")

    guest = await db.get(Guest, uuid.UUID(guestId))

    if guest is None:
        raise HTTPException(status_code=404)

    return guest
    
@app.post("/guest/disconnect")
async def disconnect_guest(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    guestId = request.cookies.get('guest_id')
    guestSessionValue = request.cookies.get('guest_session')

    if guestSessionValue:
        guestSession = await db.scalar(select(GuestSession).where(GuestSession.value == uuid.UUID(guestSessionValue)))
        if guestSession:
            await db.delete(guestSession)

    if guestId:
        guest = await db.get(Guest, uuid.UUID(guestId))
        if guest:
            await db.delete(guest)

    await db.commit()

    response.delete_cookie(key="guest_session", path="/")
    response.delete_cookie(key="guest_id", path="/")

    return {"status": "ok"}

#create a game session with a shared link
@app.post("/gamesession")
async def create_game_session(request: Request, db: AsyncSession = Depends(get_db)):
    #check if the player is a guest or a logged user
    guestId = request.cookies.get('guest_id')
    userId = request.cookies.get('user_id')

    if not guestId and not userId:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # create game session object in ram memory
    game_session = GameSession(data=jsonable_encoder(data))

    if guestId:
        guest = await db.get(Guest, uuid.UUID(guestId))
        game_session.guests.append(guest)

    if userId:
        user = await db.get(User, uuid.UUID(userId))
        game_session.users.append(user)

    await dbQuick.add_object_in_db(db, game_session)

    #id used to create a link to share with an other player
    return {"game_session": game_session.id}


#join a game session as a invited player
@app.post("/gamesession/join/{gameSessionId}")
async def join_offline_game_session(request: Request, gameSessionId: str, db: AsyncSession = Depends(get_db)):

    #check if the player is a guest
    guestId = request.cookies.get('guest_id')
    if not guestId:
        raise HTTPException(status_code=400)

    #check if the session you're tring to join exists
    result = await db.execute(select(OfflineGameSession).where(OfflineGameSession.id == gameSessionId))
    offlineGameSessionExists = result.scalars().first()
    if offlineGameSessionExists is None:
        raise HTTPException(status_code=404)
    
    result = await db.execute(
        select(GuestsGameOfflineSession).where(
            GuestsGameOfflineSession.offline_game_session_id == gameSessionId
        )
    )
    guestRows = result.scalars().all()

    #check if the session is already full or not
    if len(guestRows) >= 2:
        raise HTTPException(status_code=403)
    
    #check if the player is already in the session
    currentPlayerIsIn = any(row.guest_id == uuid.UUID(guestId) for row in guestRows)
    if currentPlayerIsIn:
        raise HTTPException(status_code=403)
    
    #add the player in the offline game session
    guestsOfflineSession = GuestsGameOfflineSession(
        offline_game_session_id=gameSessionId,
        guest_id=guestId
    )
    await dbQuick.add_object_in_db(db, guestsOfflineSession)

    return {"message": f"Joined game session with ID: {gameSessionId}"}

        
@app.websocket("/ws/chess/{gameSessionId}")
async def websocket_endpoint(websocket: WebSocket, gameSessionId: str, db: AsyncSession = Depends(get_db)):
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
            print("cookie", guestId)

            result = await db.execute(
                select(GuestsGameOfflineSession).where(
                    GuestsGameOfflineSession.offline_game_session_id == gameSessionId
                )
            )
            guestRows = result.scalars().all()

            #if the session doesn't exists close the websocket
            if guestRows is None:
                await websocket.send_text(json.dumps({"response": "Session not found"}))
                await websocket.close(code=404)
                return
    
            #wait a player if you're alone
            if len(guestRows) == 2:
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