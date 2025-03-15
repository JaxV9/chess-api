import random
import string
from sqlalchemy.orm import Session
from fastapi import Response
from datetime import timedelta
import uuid

class Generator:

    def guest_name() -> str:

        length = 32
        prefix = "Guest-"
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choices(characters, k=length))

        return prefix+random_string
    
    def guest_session_id(length = 32) -> str:
        return uuid.uuid4()

class DbQuickActions:

    def add_object_in_db(db: Session, data: object) -> None:
        db.add(data)  # Add object into the session
        db.commit()  # Save data in database
        db.refresh(data) #Refresh database to see the result


class Cookie:

    def send_cookie_for_guest(response:Response,value: str) -> None:
        response.set_cookie(
        key="guest_session",
        value=value,
        max_age=timedelta(hours=1),
        expires=timedelta(hours=1),
        #secure=True,                 # Unique access with  https
        #httponly=True,               # Don't be accessible with js
        #samesite="Strict"            # Cookie send only for a specific domain
    )