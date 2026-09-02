from database import database
from database import database
from database import database
from database import database
from database import database
from constant.constant import data
from fastapi.encoders import jsonable_encoder
import json, uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, union_all
from fastapi import FastAPI, WebSocket, Depends, Response, HTTPException, Request, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database.database import get_db
from utils.utils import Generator as gen, DbQuickActions as dbQuick, Cookie as cook
from schema.schema import ChessAction, UserSchema, GuestSchema
from model.model import User, Guest, GuestSession, GameSession, guest_game_session, user_game_session
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
active_connections: dict[str, set[WebSocket]] = {}

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
    cook.send_cookie(response, "guest_session", sessionId)
    cook.send_cookie(response, "guest_id", guest_id)

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

@app.get("/infos")
async def get_infos(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    guestId = request.cookies.get('guest_id')
    userId = request.cookies.get('user_id')
    gameSessionCookie = request.cookies.get('game_session')

    #check if cookie exists but not in db, then delete cookie
    if gameSessionCookie:
        gameSession = await db.get(GameSession, uuid.UUID(gameSessionCookie))
        if not gameSession:
            response.delete_cookie(key="game_session", path="/")

    if guestId:
        guest_uuid = uuid.UUID(guestId)
        result = await db.execute(
            select(guest_game_session.c.game_session_id).where(guest_game_session.c.guest_id == guest_uuid)
        )
        guestGameSession = result.first()
        if guestGameSession:
            return {
                "game_session": guestGameSession.game_session_id
            }
    
    if userId:
        user_uuid = uuid.UUID(userId)
        result = await db.execute(
            select(user_game_session.c.game_session_id).where(user_game_session.c.user_id == user_uuid)
        )
        userGameSession = result.first()
        if userGameSession:
            return {
                "game_session": userGameSession.game_session_id
            }

    raise HTTPException(status_code=404, detail="Have no session")


    
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
    response.delete_cookie(key="game_session", path="/")

    return {"status": "ok"}

#create a game session id
@app.post("/gamesession")
async def create_game_session(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    #check if the player is a guest or a logged user
    guestId = request.cookies.get('guest_id')
    userId = request.cookies.get('user_id')

    if not guestId and not userId:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # create game session object in ram memory
    game_session = GameSession(data=jsonable_encoder(data))

    if guestId:
        #check if guest have already a game session in db
        guest_uuid = uuid.UUID(guestId)
        guestGameSession = await db.execute(
            select(guest_game_session.c.guest_id).where(guest_game_session.c.guest_id == guest_uuid)
        )
        if guestGameSession.first() is not None:
            raise HTTPException(status_code=403, detail="Already have a game session")

        guest = await db.get(Guest, guest_uuid)
        game_session.guests.append(guest)

    if userId:
        #check if user have already a game session in db
        user_uuid = uuid.UUID(userId)
        userGameSession = await db.execute(
            select(user_game_session.c.user_id).where(user_game_session.c.user_id == user_uuid)
        )
        if userGameSession.first() is not None:
            raise HTTPException(status_code=403, detail="Already have a game session")

        user = await db.get(User, user_uuid)
        game_session.users.append(user)

    await dbQuick.add_object_in_db(db, game_session)

    cook.send_cookie(response, "game_session", str(game_session.id))


    #id used to create a link to share with an other player
    return {"game_session": game_session.id}


#join a game session as a guest player or a logged user, for player that don't have create the game session
@app.post("/gamesession/join/{gameSessionId}")
async def join_game_session(request: Request, response: Response, gameSessionId: str, db: AsyncSession = Depends(get_db)):

    #check if the player is a guest
    guestId = request.cookies.get('guest_id')
    userId = request.cookies.get('user_id')
    session_uuid = uuid.UUID(gameSessionId)

    if not guestId and not userId:
        raise HTTPException(status_code=401)

    #check if the session you're tring to join exists
    gameSession = await db.get(GameSession, session_uuid)
    if gameSession is None:
        raise HTTPException(status_code=404)

    await db.refresh(gameSession, ["guests", "users"])

    guest_rows = (await db.execute(
        select(guest_game_session.c.guest_id).where(guest_game_session.c.game_session_id == session_uuid)
    )).all()

    user_rows = (await db.execute(
        select(user_game_session.c.user_id).where(user_game_session.c.game_session_id == session_uuid)
    )).all()

    #check if the session is already full or not
    if len(guest_rows) + len(user_rows) >= 2:
        raise HTTPException(status_code=403, detail="a")
    
    #check if the player is already in the session
    if guestId:
        currentGuestInSession = await db.execute(
            select(guest_game_session).where(
                guest_game_session.c.guest_id == uuid.UUID(guestId)
            )
        )
        if currentGuestInSession.first() is not None:
            raise HTTPException(status_code=403, detail="b")

        guestUuid = uuid.UUID(guestId)
        guest = await db.get(Guest, guestUuid)
        gameSession.guests.append(guest)
        await db.commit()
        cook.send_cookie(response, "game_session", gameSessionId)
        return {"game_session": gameSessionId}


    elif userId:
        currentUserInSession = await db.execute(
            select(user_game_session).where(
                user_game_session.c.user_id == uuid.UUID(userId)
            )
        )
        if currentUserInSession.first() is not None:
            raise HTTPException(status_code=403, detail="c")

        userUuid = uuid.UUID(userId)
        user = await db.get(User, userUuid)
        gameSession.users.append(user)
        await db.commit()
        cook.send_cookie(response, "game_session", gameSessionId)
        return {"game_session": gameSessionId}
    
    raise HTTPException(status_code=403, detail="d")

        
@app.websocket("/ws/chess/{gameSessionId}")
async def websocket_endpoint(websocket: WebSocket, gameSessionId: str, db: AsyncSession = Depends(get_db)):
    await websocket.accept()

    try:
        #Test if the uuid format is correct
        try:
            uuid.UUID(gameSessionId)
        except ValueError:
            await websocket.close(code=403)
            return
        
        gameSession = await db.get(GameSession, uuid.UUID(gameSessionId))

        #if the session doesn't exists in db close the websocket
        if gameSession is None:
            await websocket.send_text(json.dumps({"response": "Session not found"}))
            await websocket.close(code=404)
            return

        if gameSessionId not in active_connections:
            active_connections[gameSessionId] = set()
        
        active_connections[gameSessionId].add(websocket)

        session_data = gameSession.data

        playersSessions = list(active_connections.get(gameSessionId, set()))

        response = {"response": "ok", "data": session_data }

        playersQuery = union_all(
            select(Guest.username)
            .join(guest_game_session, Guest.id == guest_game_session.c.guest_id)
            .where(guest_game_session.c.game_session_id == gameSession.id),

            select(User.username)
            .join(user_game_session, User.id == user_game_session.c.user_id)
            .where(user_game_session.c.game_session_id == gameSession.id)
        )

        usernamesOfPlayers = (await db.execute(playersQuery)).scalars().all()

        response["players"] = []

        for username in usernamesOfPlayers:
            response["players"].append({
                "username" : username
            })

        if len(playersSessions) == 1:
            response["waiting_player"] = True
            await websocket.send_text(json.dumps(jsonable_encoder(response)))
            
        if len(playersSessions) == 2:
            response["waiting_player"] = False
            
            for connection in playersSessions:
                await connection.send_text(json.dumps(jsonable_encoder(response)))

        while True:

            #wait a message from client
            message = await websocket.receive_text()

            chessAction = ChessAction.model_validate_json(message)

            if chessAction.action == "move":
                for piece in chessAction.pieces:
                    for data_piece in session_data:
                        if data_piece["id"] == piece.id:
                            data_piece["pos"] = piece.pos
                            break
                gameSession.data = session_data
                db.add(gameSession)
                await db.commit()
                await db.refresh(gameSession)

                # Send updated data to all clients
                for connection in list(active_connections.get(gameSessionId, set())):
                    try:
                        await connection.send_text(json.dumps(jsonable_encoder(response)))
                    except Exception:
                        active_connections[gameSessionId].discard(connection)

    except WebSocketDisconnect as e:
        print(f"Client disconnected: {e}")
        active_connections.get(gameSessionId, set()).discard(websocket)
        if not active_connections.get(gameSessionId):
            del active_connections[gameSessionId]