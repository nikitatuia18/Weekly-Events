from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timedelta
from typing import Optional, List
import models, schemas

# User CRUD
def get_user_by_telegram_id(db: Session, telegram_id: int):
    return db.query(models.User).filter(models.User.telegram_id == telegram_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_or_create_user(db: Session, telegram_id: int, username: str, first_name: str):
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        user = create_user(db, schemas.UserCreate(telegram_id=telegram_id, username=username, first_name=first_name))
    return user

def update_user_balance(db: Session, user_id: int, amount: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.balance += amount
        db.commit()
        db.refresh(user)
    return user

def update_user_bonus_time(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.last_bonus_time = datetime.utcnow()
        db.commit()
        db.refresh(user)
    return user

def get_leaderboard(db: Session, limit: int = 10):
    # Subquery to get last correct bet time for each user
    # This is complex: need max(created_at) from bets where choice = event.winning_outcome
    # We'll implement a simpler version: use the latest bet time among correct bets.
    # For MVP, we can join bets and events, filter choice=winning_outcome, get max time per user.
    subq = db.query(
        models.Bet.user_id,
        func.max(models.Bet.created_at).label('last_correct_time')
    ).join(models.Event, models.Event.id == models.Bet.event_id)\
     .filter(models.Event.winning_outcome == models.Bet.choice)\
     .group_by(models.Bet.user_id).subquery()

    query = db.query(
        models.User.id,
        models.User.username,
        models.User.first_name,
        models.User.weekly_score,
        subq.c.last_correct_time
    ).outerjoin(subq, models.User.id == subq.c.user_id)\
     .order_by(desc(models.User.weekly_score), subq.c.last_correct_time.asc())\
     .limit(limit)

    results = []
    for row in query.all():
        results.append({
            "user_id": row.id,
            "username": row.username,
            "first_name": row.first_name,
            "weekly_score": row.weekly_score,
            "last_correct_bet_time": row.last_correct_time,
        })
    return results

def get_user_rank_and_score(db: Session, user_id: int):
    # Get user's score
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None, None
    score = user.weekly_score

    # Rank based on same logic as leaderboard
    subq = db.query(
        models.Bet.user_id,
        func.max(models.Bet.created_at).label('last_correct_time')
    ).join(models.Event, models.Event.id == models.Bet.event_id)\
     .filter(models.Event.winning_outcome == models.Bet.choice)\
     .group_by(models.Bet.user_id).subquery()

    # Count users with higher score or same score and earlier correct bet
    # Since we need rank, we can query all users with ordering and then find position.
    all_users = db.query(
        models.User.id,
        models.User.weekly_score,
        subq.c.last_correct_time
    ).outerjoin(subq, models.User.id == subq.c.user_id)\
     .order_by(desc(models.User.weekly_score), subq.c.last_correct_time.asc()).all()

    rank = None
    for idx, row in enumerate(all_users, start=1):
        if row.id == user_id:
            rank = idx
            break
    return score, rank

# Event CRUD
def get_active_events(db: Session):
    now = datetime.utcnow()
    return db.query(models.Event).filter(
        models.Event.status == "active",
        models.Event.deadline > now
    ).all()

def get_event(db: Session, event_id: int):
    return db.query(models.Event).filter(models.Event.id == event_id).first()

def create_event(db: Session, event: schemas.EventCreate):
    db_event = models.Event(**event.dict(), status="active")
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def update_event(db: Session, event_id: int, event_update: schemas.EventUpdate):
    db_event = get_event(db, event_id)
    if db_event and db_event.status == "active":
        update_data = event_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_event, field, value)
        db.commit()
        db.refresh(db_event)
    return db_event

def resolve_event(db: Session, event_id: int, winning_outcome: str):
    db_event = get_event(db, event_id)
    if not db_event or db_event.status != "active":
        return None
    db_event.status = "resolved"
    db_event.winning_outcome = winning_outcome
    # Update scores for users who bet correctly
    correct_bets = db.query(models.Bet).filter(
        models.Bet.event_id == event_id,
        models.Bet.choice == winning_outcome
    ).all()
    for bet in correct_bets:
        user = db.query(models.User).filter(models.User.id == bet.user_id).first()
        if user:
            user.weekly_score += 1
    db.commit()
    return db_event

def get_all_events(db: Session):
    return db.query(models.Event).order_by(models.Event.deadline.desc()).all()

# Bet CRUD
def get_user_bet_for_event(db: Session, user_id: int, event_id: int):
    return db.query(models.Bet).filter(
        models.Bet.user_id == user_id,
        models.Bet.event_id == event_id
    ).first()

def place_bet(db: Session, user_id: int, event_id: int, choice: str):
    # Check balance
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user.balance < 50:
        return None, "Insufficient balance"
    event = get_event(db, event_id)
    if not event or event.status != "active" or event.deadline < datetime.utcnow():
        return None, "Event not available"
    existing = get_user_bet_for_event(db, user_id, event_id)
    if existing:
        return None, "Already placed bet"
    # Deduct balance
    user.balance -= 50
    bet = models.Bet(user_id=user_id, event_id=event_id, choice=choice)
    db.add(bet)
    db.commit()
    db.refresh(bet)
    return bet, None

def get_user_bets(db: Session, user_id: int):
    return db.query(models.Bet).filter(models.Bet.user_id == user_id).join(models.Event).order_by(models.Bet.created_at.desc()).all()

# Weekly Winner CRUD
def determine_weekly_winner(db: Session):
    # Use same ordering logic as leaderboard
    subq = db.query(
        models.Bet.user_id,
        func.max(models.Bet.created_at).label('last_correct_time')
    ).join(models.Event, models.Event.id == models.Bet.event_id)\
     .filter(models.Event.winning_outcome == models.Bet.choice)\
     .group_by(models.Bet.user_id).subquery()

    top_user = db.query(
        models.User.id,
        models.User.username,
        models.User.weekly_score,
        subq.c.last_correct_time
    ).outerjoin(subq, models.User.id == subq.c.user_id)\
     .filter(models.User.weekly_score > 0)\
     .order_by(desc(models.User.weekly_score), subq.c.last_correct_time.asc()).first()

    if not top_user:
        return None

    winner_id = top_user.id
    # Determine week boundaries (Sunday 23:59 UTC)
    now = datetime.utcnow()
    # Find last Sunday 23:59
    days_since_sunday = now.weekday() + 1 if now.weekday() != 6 else 0
    last_sunday = (now - timedelta(days=days_since_sunday)).replace(hour=23, minute=59, second=0, microsecond=0)
    week_start = (last_sunday - timedelta(days=6)).date()
    week_end = last_sunday.date()

    # Create winner record
    winner_record = models.WeeklyWinner(
        week_start=week_start,
        week_end=week_end,
        winner_user_id=winner_id,
        prize_amount=50.00,
        paid=False
    )
    db.add(winner_record)
    # Reset all weekly scores
    db.query(models.User).update({models.User.weekly_score: 0})
    db.commit()
    db.refresh(winner_record)
    return winner_record

def get_weekly_winners(db: Session):
    return db.query(models.WeeklyWinner).order_by(models.WeeklyWinner.week_end.desc()).all()
