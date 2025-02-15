from dataclasses import dataclass

@dataclass
class ChessPiece():
    id: str
    role: str
    color: str
    pos: int