from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional

# User schemas
class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    balance: int
    weekly_score: int
    last_bonus_time: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserPublic(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    weekly_score: int

# Event schemas
class EventBase(BaseModel):
    title: str
    outcome_a: str
    outcome_b: str
    deadline: datetime

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    outcome_a: Optional[str] = None
    outcome_b: Optional[str] = None
    deadline: Optional[datetime] = None

class Event(EventBase):
    id: int
    status: str
    winning_outcome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Bet schemas
class BetCreate(BaseModel):
    event_id: int
    choice: str  # 'A' or 'B'

class Bet(BaseModel):
    id: int
    user_id: int
    event_id: int
    choice: str
    created_at: datetime

    class Config:
        from_attributes = True

class BetWithEvent(Bet):
    event: Event

# WeeklyWinner schemas
class WeeklyWinnerBase(BaseModel):
    week_start: date
    week_end: date
    winner_user_id: int
    prize_amount: float
    paid: bool = False

class WeeklyWinner(WeeklyWinnerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Leaderboard entry
class LeaderboardEntry(BaseModel):
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    weekly_score: int
    last_correct_bet_time: Optional[datetime] = None
    rank: Optional[int] = None
