import random
import string
from sqlalchemy.ext.asyncio import AsyncSession
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
    
    @staticmethod
    async def add_object_in_db(db: AsyncSession, data: object) -> None:
        db.add(data)          # Add object into the session
        await db.commit()     # Save data in database
        await db.refresh(data) # Refresh database to see the result

    @staticmethod
    async def delete_object_in_db(db: AsyncSession, data: object) -> None:
        await db.delete(data) # Remove object into the session
        await db.commit()     # Save data in database


class Cookie:

    @staticmethod
    def send_cookie_for_guest(response: Response, key: str, value: str) -> None:
        expire_time = datetime.now(timezone.utc) + timedelta(hours=1)
        response.set_cookie(
            key=key,
            value=value,
            max_age=3600,  # in seconds
            expires=expire_time,
            secure=False,
            httponly=True,
            samesite="lax",  # "None" requires secure=True (HTTPS) — use lax for local dev
            path="/", 
        )