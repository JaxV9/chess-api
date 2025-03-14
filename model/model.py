from sqlalchemy import Integer, String, ForeignKey, Column, Table, JSON, DateTime, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from typing import List, Optional
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

user_game_session = Table(
    "user_game_session",
    Base.metadata,
    Column("user_id", UUID, ForeignKey("user.id"), primary_key=True),
    Column("game_session_id", Integer, ForeignKey("game_session.id"), primary_key=True)
)


class User(Base):
    __tablename__ = "user"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, unique=True)
    email: Mapped[str] = mapped_column(String, index=True, unique=True)
    username: Mapped[str] = mapped_column(String, index=True, unique=True)
    password: Mapped[str] = mapped_column(String)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), index=True, server_default=func.now())

    statistic: Mapped["Statistic"] = relationship("Statistic", back_populates="user", uselist=False)

    game_sessions: Mapped[Optional["GameSession"]] = relationship(
        "GameSession", secondary=user_game_session, back_populates="users", uselist=False
    )


    def __repr__(self):
        return f"id: {self.id} email: {self.email} username: {self.username} created_at: {self.created_at}"


class Statistic(Base):
    __tablename__ = "statistic"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    win: Mapped[str] = mapped_column(Integer, index=True)
    loss: Mapped[str] = mapped_column(Integer, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"))

    user: Mapped["User"] = relationship("User", back_populates="statistic")

    def __repr__(self):
        return f"id: {self.id} win: {self.win} loss: {self.loss} created_at: {self.created_at}"


class GameSession(Base):
    __tablename__ = "game_session"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime, index=True, server_default=func.now(),)
    time: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, index=True, nullable=True)

    users: Mapped[List["User"]] = relationship(
        "User", secondary=user_game_session, back_populates="game_sessions"
    )

    def __repr__(self):
        return f"id: {self.id} data: {self.data} parents: {self.parents}"
