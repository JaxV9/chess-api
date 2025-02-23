from dataclasses import dataclass
from typing import List
from pydantic import BaseModel

@dataclass
class ChessPiece():
    id: str
    role: str
    color: str
    pos: int

class ChessAction(BaseModel):
    action: str
    pieces: List[ChessPiece]