"""Modèles SQLAlchemy pour la BDD PostgreSQL (contrat aligné avec l'API et l'app mobile)."""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    game_players: Mapped[list["GamePlayer"]] = relationship(back_populates="player")
    round_results: Mapped[list["RoundResult"]] = relationship(back_populates="player")


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="waiting")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_rounds: Mapped[int] = mapped_column(Integer, default=0)

    game_players: Mapped[list["GamePlayer"]] = relationship(back_populates="game")
    round_results: Mapped[list["RoundResult"]] = relationship(back_populates="game")


class Phrase(Base):
    __tablename__ = "phrases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    round_results: Mapped[list["RoundResult"]] = relationship(back_populates="phrase")


class GamePlayer(Base):
    __tablename__ = "game_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    final_score: Mapped[int] = mapped_column(Integer, default=0)
    rank_in_game: Mapped[int | None] = mapped_column(Integer, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="game_players")
    player: Mapped["Player"] = relationship(back_populates="game_players")


class RoundResult(Base):
    __tablename__ = "round_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    round_index: Mapped[int] = mapped_column(Integer, nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    phrase_id: Mapped[int | None] = mapped_column(ForeignKey("phrases.id", ondelete="SET NULL"), nullable=True)
    time_taken: Mapped[float] = mapped_column(Float, nullable=False)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    score_added: Mapped[int] = mapped_column(Integer, default=0)
    objects_triggered: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="round_results")
    player: Mapped["Player"] = relationship(back_populates="round_results")
    phrase: Mapped["Phrase | None"] = relationship(back_populates="round_results")
