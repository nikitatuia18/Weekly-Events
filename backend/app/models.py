from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, DECIMAL, Date, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    balance = Column(Integer, default=0)
    weekly_score = Column(Integer, default=0)
    last_bonus_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    outcome_a = Column(String(255), nullable=False)
    outcome_b = Column(String(255), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="active")  # active, closed, resolved
    winning_outcome = Column(String(1), nullable=True)  # 'A', 'B', or NULL
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Bet(Base):
    __tablename__ = "bets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    choice = Column(String(1), nullable=False)  # 'A' or 'B'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('user_id', 'event_id', name='_user_event_uc'),)

class WeeklyWinner(Base):
    __tablename__ = "weekly_winners"
    id = Column(Integer, primary_key=True, index=True)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    winner_user_id = Column(Integer, ForeignKey("users.id"))
    prize_amount = Column(DECIMAL(10,2), nullable=False)
    paid = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
