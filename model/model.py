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
    created_at: Mapped[DateTime] = mapped_column(DateTime, index=True, server_default=func.now())
    time: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, index=True, nullable=True)

    users: Mapped[List["User"]] = relationship(
        "User", secondary=user_game_session, back_populates="game_sessions"
    )

    def __repr__(self):
        return f"id: {self.id} data: {self.data} parents: {self.users}"


#-----------------Start of: models for guest players-----------------#
class GuestsGameOfflineSession(Base):
    __tablename__ = "guests_game_offline_session"

    guest_id = Column(UUID, ForeignKey("guest.id"), primary_key=True, unique=True)
    offline_game_session_id = Column(UUID, ForeignKey("offline_game_session.id"), primary_key=True)

    # Optionnel : Ajouter une relation avec les modèles Guest et OfflineGameSession
    guest = relationship("Guest", back_populates="guests_game_offline_sessions")
    offline_game_session = relationship("OfflineGameSession", back_populates="guests_game_offline_sessions")


class Guest(Base):
    __tablename__ = "guest"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, unique=True)
    username: Mapped[str] = mapped_column(String, index=True, unique=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), index=True, server_default=func.now())
    gest_session: Mapped[Optional["GuestSession"]] = relationship("GuestSession", back_populates="guest", uselist=False)
    
    offline_game_sessions: Mapped[Optional["OfflineGameSession"]] = relationship(
        "OfflineGameSession", secondary=GuestsGameOfflineSession.__table__, back_populates="guests")
    guests_game_offline_sessions: Mapped[Optional["GuestsGameOfflineSession"]] = relationship("GuestsGameOfflineSession", back_populates="guest", uselist=False)


class GuestSession(Base):
    __tablename__ = "gest_session"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    value: Mapped[UUID] = mapped_column(UUID(as_uuid=True), index=True, unique=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, index=True, server_default=func.now())
    guest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("guest.id"), unique=True)
    guest: Mapped["Guest"] = relationship("Guest", back_populates="gest_session")


class OfflineGameSession(Base):

    __tablename__ = "offline_game_session"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, unique=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime, index=True, server_default=func.now())
    time: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, index=True, nullable=True)

    guests: Mapped[List["Guest"]] = relationship(
        "Guest", secondary=GuestsGameOfflineSession.__table__, back_populates="offline_game_sessions"
    )
    guests_game_offline_sessions: Mapped[List["GuestsGameOfflineSession"]] = relationship("GuestsGameOfflineSession", back_populates="offline_game_session")

    def __repr__(self):
        return f"id: {self.id} data: {self.data} parents: {self.guest}"
#-----------------End of: models for guest players-----------------#