from database import database
from constant.constant import data
from fastapi.encoders import jsonable_encoder
import json, uuid, asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, union_all
from fastapi import FastAPI, WebSocket, Depends, Response, HTTPException, Request, WebSocketDisconnect
from sqlalchemy.orm.attributes import flag_modified
from fastapi.middleware.cors import CORSMiddleware
from database.database import get_db, AsyncSessionLocal
from utils.utils import Generator as gen, DbQuickActions as dbQuick, Cookie as cook
from schema.schema import ChessAction, UserSchema, GuestSchema
from model.model import User, Guest, GuestSession, GameSession, guest_game_session, user_game_session
import os
import random

base_url = (os.getenv("BASE_URL") or "").rstrip("/")

origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

if base_url:
    origins.append(base_url)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
active_connections: dict[str, set[WebSocket]] = {}
session_players: dict[str, dict[str, str]] = {}

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
    guest_session = GuestSession(
        value=sessionId,
        guest_id=guest_id
    )
    await dbQuick.add_object_in_db(db, guest_session)
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
    guest_id = request.cookies.get('guest_id')
    user_id = request.cookies.get('user_id')
    game_session_cookie = request.cookies.get('game_session')

    #check if cookie exists but not in db, then delete cookie
    if game_session_cookie:
        game_session = await db.get(GameSession, uuid.UUID(game_session_cookie))
        if not game_session:
            cook.delete_cookie(response, "game_session")

    if guest_id:
        guest_uuid = uuid.UUID(guest_id)
        result = await db.execute(
            select(guest_game_session.c.game_session_id).where(guest_game_session.c.guest_id == guest_uuid)
        )
        guest_game_session_query = result.first()
        if guest_game_session_query:
            return {
                "game_session": guest_game_session_query.game_session_id
            }
    
    if user_id:
        user_uuid = uuid.UUID(user_id)
        result = await db.execute(
            select(user_game_session.c.game_session_id).where(user_game_session.c.user_id == user_uuid)
        )
        user_game_session_query = result.first()
        if user_game_session_query:
            return {
                "game_session": user_game_session_query.game_session_id
            }

    raise HTTPException(status_code=404, detail="Have no session")


@app.post("/quitgame")
async def quit_game(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    game_session_value = request.cookies.get('game_session')

    if game_session_value:

        connections = active_connections.get(game_session_value, set()).copy()
        for ws in connections:
            try:
                await ws.send_text(json.dumps({
                    "response": "opponent_quit",
                }))
                await ws.close()
            except Exception:
                pass

        active_connections.pop(game_session_value, None)
        session_players.pop(game_session_value, None)


        game_session = await db.get(GameSession, uuid.UUID(game_session_value))
        if game_session:
            await db.delete(game_session)
            await db.commit()

    cook.delete_cookie(response, "game_session")

    return {"status": "ok"}

    
@app.post("/guest/disconnect")
async def disconnect_guest(request: Request, response: Response, db: AsyncSession = Depends(get_db)):

    guestId = request.cookies.get('guest_id')
    guest_session_value = request.cookies.get('guest_session')

    if guestId:
        guest_uuid = uuid.UUID(guestId)
        game_session_result = await db.execute(
            select(guest_game_session.c.game_session_id).where(guest_game_session.c.guest_id == guest_uuid)
        )
        game_session_row = game_session_result.first()
        if game_session_row:
            game_session_id_str = str(game_session_row.game_session_id)
            connections = active_connections.get(game_session_id_str, set()).copy()
            for ws in connections:
                try:
                    await ws.send_text(json.dumps({"response": "opponent_quit"}))
                    await ws.close()
                except Exception:
                    pass
            active_connections.pop(game_session_id_str, None)
            session_players.pop(game_session_id_str, None)

            game_session_obj = await db.get(GameSession, game_session_row.game_session_id)
            if game_session_obj:
                await db.delete(game_session_obj)
                await db.commit()

    cook.delete_cookie(response, "game_session")

    if guest_session_value:
        guestSession = await db.scalar(select(GuestSession).where(GuestSession.value == uuid.UUID(guest_session_value)))
        if guestSession:
            await db.delete(guestSession)

    if guestId:
        guest = await db.get(Guest, uuid.UUID(guestId))
        if guest:
            await db.delete(guest)

    await db.commit()

    cook.delete_cookie(response, "guest_session")
    cook.delete_cookie(response, "guest_id")
    cook.delete_cookie(response, "game_session")

    return {"status": "ok"}

#create a game session id
@app.post("/gamesession")
async def create_game_session(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    #check if the player is a guest or a logged user
    guest_id = request.cookies.get('guest_id')
    user_id = request.cookies.get('user_id')

    if not guest_id and not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # create game session object in ram memory
    game_session = GameSession(data=jsonable_encoder(data), history=[])

    if guest_id:
        #check if guest have already a game session in db
        guest_uuid = uuid.UUID(guest_id)
        guest_game_session_query = await db.execute(
            select(guest_game_session.c.guest_id).where(guest_game_session.c.guest_id == guest_uuid)
        )
        if guest_game_session_query.first() is not None:
            raise HTTPException(status_code=403, detail="Already have a game session")

        guest = await db.get(Guest, guest_uuid)
        game_session.guests.append(guest)

    if user_id:
        #check if user have already a game session in db
        user_uuid = uuid.UUID(user_id)
        user_game_session_query = await db.execute(
            select(user_game_session.c.user_id).where(user_game_session.c.user_id == user_uuid)
        )
        if user_game_session_query.first() is not None:
            raise HTTPException(status_code=403, detail="Already have a game session")

        user = await db.get(User, user_uuid)
        game_session.users.append(user)

    await dbQuick.add_object_in_db(db, game_session)

    cook.send_cookie(response, "game_session", str(game_session.id))


    #id used to create a link to share with an other player
    return {"game_session": game_session.id}


#join a game session as a guest player or a logged user, for player that don't have create the game session
@app.post("/gamesession/join/{game_session_id}")
async def join_game_session(request: Request, response: Response, game_session_id: str, db: AsyncSession = Depends(get_db)):

    #check if the player is a guest
    guest_id = request.cookies.get('guest_id')
    user_id = request.cookies.get('user_id')
    session_uuid = uuid.UUID(game_session_id)

    if not guest_id and not user_id:
        raise HTTPException(status_code=401)

    #check if the session you're tring to join exists
    game_session = await db.get(GameSession, session_uuid)
    if game_session is None:
        raise HTTPException(status_code=404)

    await db.refresh(game_session, ["guests", "users"])

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
    if guest_id:
        current_guest_in_session = await db.execute(
            select(guest_game_session).where(
                guest_game_session.c.guest_id == uuid.UUID(guest_id)
            )
        )
        if current_guest_in_session.first() is not None:
            raise HTTPException(status_code=403, detail="b")

        guest_uuid = uuid.UUID(guest_id)
        guest = await db.get(Guest, guest_uuid)
        game_session.guests.append(guest)
        await db.commit()
        cook.send_cookie(response, "game_session", game_session_id)
        return {"game_session": game_session_id}


    elif user_id:
        currentUserInSession = await db.execute(
            select(user_game_session).where(
                user_game_session.c.user_id == uuid.UUID(user_id)
            )
        )
        if currentUserInSession.first() is not None:
            raise HTTPException(status_code=403, detail="c")

        userUuid = uuid.UUID(user_id)
        user = await db.get(User, userUuid)
        game_session.users.append(user)
        await db.commit()
        cook.send_cookie(response, "game_session", game_session_id)
        return {"game_session": game_session_id}
    
    raise HTTPException(status_code=403, detail="")

        
@app.websocket("/ws/chess/{game_session_id}")
async def websocket_endpoint(websocket: WebSocket, game_session_id: str):
    await websocket.accept()

    try:
        # Test if the uuid format is correct
        try:
            session_uuid = uuid.UUID(game_session_id)
        except ValueError:
            await websocket.close(code=403)
            return

        game_session = None
        usernames_of_players = []
        session_data = None
        session_history = None

        for _ in range(5):
            async with AsyncSessionLocal() as db:
                game_session = await db.get(GameSession, session_uuid)
                if game_session is not None:
                    session_data = game_session.data
                    session_history = game_session.history

                    players_query = union_all(
                        select(Guest.username)
                        .join(guest_game_session, Guest.id == guest_game_session.c.guest_id)
                        .where(guest_game_session.c.game_session_id == session_uuid),

                        select(User.username)
                        .join(user_game_session, User.id == user_game_session.c.user_id)
                        .where(user_game_session.c.game_session_id == session_uuid)
                    )

                    usernames_of_players = (await db.execute(players_query)).scalars().all()
                    break
            await asyncio.sleep(0.4)

        # if the session doesn't exists in db close the websocket
        if game_session is None:
            await websocket.send_text(json.dumps({"response": "Session not found"}))
            await websocket.close(code=404)
            return

        if game_session_id not in active_connections:
            active_connections[game_session_id] = set()
        
        active_connections[game_session_id].add(websocket)

        players_sessions = list(active_connections.get(game_session_id, set()))

        response = {"response": "ok", "data": session_data, "history": session_history}

        response["players"] = []

        # colors assignment
        if game_session_id not in session_players:
            session_players[game_session_id] = {}

        for username in usernames_of_players:
            if username not in session_players[game_session_id]:
                if len(session_players[game_session_id]) == 0:
                    session_players[game_session_id][username] = "white" if bool(random.getrandbits(1)) else "black"
                else:
                    first_color = next(iter(session_players[game_session_id].values()))
                    session_players[game_session_id][username] = "black" if first_color == "white" else "white"

            response["players"].append({
                "username": username,
                "color": session_players[game_session_id][username]
            })

        if len(players_sessions) == 1:
            response["waiting_player"] = True
            await websocket.send_text(json.dumps(jsonable_encoder(response)))
            
        if len(players_sessions) == 2:
            response["waiting_player"] = False
            player_with_white_color = next(
                (user for user, color in session_players[game_session_id].items() if color == "white"),
                None
            )
            if player_with_white_color is None:
                return HTTPException(status_code=404)

            if "user_to_play" not in session_players[game_session_id]:
                session_players[game_session_id]["user_to_play"] = player_with_white_color

            response["user_to_play"] = session_players[game_session_id]["user_to_play"]
            for connection in players_sessions:
                await connection.send_text(json.dumps(jsonable_encoder(response)))

        while True:

            # wait a message from client
            message = await websocket.receive_text()

            chessAction = ChessAction.model_validate_json(message)

            async with AsyncSessionLocal() as db:
                game_session = await db.get(GameSession, session_uuid)
                if game_session is None:
                    continue

                session_data = game_session.data

                if len(session_data) > len(chessAction.pieces):
                    old_ids = { session["id"] for session in session_data }
                    new_ids = { piece.id for piece in chessAction.pieces }

                    captured_piece = old_ids - new_ids
                    session_data = [data_piece for data_piece in session_data if data_piece["id"] not in captured_piece]

                if chessAction.action == "move":
                    for piece in chessAction.pieces:
                        for data_piece in session_data:
                            if data_piece["id"] == piece.id:
                                if data_piece["pos"] != piece.pos:
                                    current_history = game_session.history or []
                                    game_session.history = [*current_history, {
                                        "piece_id": piece.id,
                                        "from": data_piece["pos"],
                                        "to": piece.pos
                                    }]
                                    flag_modified(game_session, "history")
                                data_piece["pos"] = piece.pos
                                break
                    game_session.data = session_data
                    flag_modified(game_session, "data")
                    db.add(game_session)
                    await db.commit()
                    updated_history = game_session.history

            if chessAction.action == "move":
                response["data"] = session_data
                response["history"] = updated_history

                response["players"] = [
                    {"username": user, "color": color}
                    for user, color in session_players[game_session_id].items()
                    if user != "user_to_play"
                ]

                # Send updated data to all clients
                current_connections = list(active_connections.get(game_session_id, set()))
                response["waiting_player"] = len(current_connections) < 2

                player_with_white_color = next(
                    (user for user, color in session_players[game_session_id].items() if color == "white"),
                    None
                )

                player_with_black_color = next(
                    (user for user, color in session_players[game_session_id].items() if color == "black"),
                    None
                )

                # change the turn of the user to play
                if session_players[game_session_id]["user_to_play"] == player_with_white_color:
                    session_players[game_session_id]["user_to_play"] = player_with_black_color
                else:
                    session_players[game_session_id]["user_to_play"] = player_with_white_color

                response["user_to_play"] = session_players[game_session_id]["user_to_play"]

                for connection in current_connections:
                    try:
                        await connection.send_text(json.dumps(jsonable_encoder(response)))
                    except Exception:
                        active_connections[game_session_id].discard(connection)

    except WebSocketDisconnect as e:
        print(f"Client disconnected: {e}")
        active_connections.get(game_session_id, set()).discard(websocket)
        if not active_connections.get(game_session_id):
            del active_connections[game_session_id]
            session_players.pop(game_session_id, None)