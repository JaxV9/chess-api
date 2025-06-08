import random
import string
from sqlalchemy.orm import Session
from fastapi import Response
from datetime import timedelta, datetime, timezone
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

    @staticmethod
    def send_cookie_for_guest(response: Response, key: str, value: str) -> None:
        expire_time = datetime.now(timezone.utc) + timedelta(hours=1)
        response.set_cookie(
            key=key,
            value=value,
            max_age=3600,  # en secondes
            expires=expire_time,
            secure=True,  # False pour le développement local
            httponly=True,  # Recommandé pour des raisons de sécurité
            samesite="none",  # Essayez "none" pour le développement local
            path="/",  # Assurez-vous que le cookie est envoyé pour le bon chemin
        )