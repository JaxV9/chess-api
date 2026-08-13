from dataclasses import dataclass
from typing import List, Optional
from pydantic import BaseModel, UUID4, EmailStr, ConfigDict
from datetime import datetime

@dataclass
class ChessPiece():
    id: str
    role: str
    color: str
    pos: int

class ChessAction(BaseModel):
    action: str
    pieces: List[ChessPiece]


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    email: EmailStr
    username: str
    created_at: datetime

class UserBaseSubscription(UserSchema):
    model_config = ConfigDict(from_attributes=True)

    password: str


class StatisticBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    win: int
    loss: int
    user_id: UUID4


class GameSessionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    player_1: Optional[UUID4]
    player_2: Optional[UUID4]
    data: dict


class GuestSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    username: str


class OfflineGameSessionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    guest_1: Optional[UUID4]
    guest_2: Optional[UUID4]
    data: dict
