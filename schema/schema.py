from dataclasses import dataclass
from typing import List, Optional
from pydantic import BaseModel, UUID4, EmailStr
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
    id: UUID4
    email: EmailStr
    username: str
    created_at: datetime

    class Config:
        orm_mode = True


class UserBaseSubscription(UserSchema):
    password: str

    class Config:
        orm_mode = True


class StatisticBase(BaseModel):
    id: int
    win: int
    loss: int
    user_id: UUID4

    class Config:
        orm_mode = True

class GameSessionBase(BaseModel):
    id: int
    created_at: datetime
    player_1: Optional[UUID4]
    player_2: Optional[UUID4]
    data: dict

    class Config:
        orm_mode = True
