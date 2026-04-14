from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import os

import crud, schemas, models
from database import get_db
from utils import verify_telegram_init_data, is_bonus_available

router = APIRouter(prefix="/api", tags=["api"])

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Dependency to get current user from initData
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    # Expecting header: Authorization: tma <initData>
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    init_data = authorization[4:]  # remove "tma "
    user_data = verify_telegram_init_data(init_data, BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid initData")
    telegram_id = user_data.get("telegram_id")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="No telegram_id in initData")
    user = crud.get_or_create_user(db, telegram_id, user_data.get("username"), user_data.get("first_name"))
    return user

@router.get("/user/me", response_model=schemas.User)
def get_me(user: models.User = Depends(get_current_user)):
    return user

@router.post("/user/bonus")
def claim_bonus(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_bonus_available(user.last_bonus_time):
        raise HTTPException(status_code=400, detail="Bonus not available yet")
    # Add up to max 200
    add_amount = 100
    if user.balance + add_amount > 200:
        add_amount = 200 - user.balance
    if add_amount <= 0:
        raise HTTPException(status_code=400, detail="Balance already at max")
    crud.update_user_balance(db, user.id, add_amount)
    crud.update_user_bonus_time(db, user.id)
    return {"balance": user.balance + add_amount, "added": add_amount}

@router.get("/events/active", response_model=List[schemas.Event])
def get_active_events(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    events = crud.get_active_events(db)
    return events

@router.post("/bets", response_model=schemas.Bet)
def place_bet(
    bet_data: schemas.BetCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    bet, error = crud.place_bet(db, user.id, bet_data.event_id, bet_data.choice)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return bet

@router.get("/bets/my", response_model=List[schemas.BetWithEvent])
def get_my_bets(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    bets = crud.get_user_bets(db, user.id)
    # Attach event info
    result = []
    for bet in bets:
        event = crud.get_event(db, bet.event_id)
        bet_with_event = schemas.BetWithEvent(
            id=bet.id,
            user_id=bet.user_id,
            event_id=bet.event_id,
            choice=bet.choice,
            created_at=bet.created_at,
            event=schemas.Event.from_orm(event)
        )
        result.append(bet_with_event)
    return result

@router.get("/leaderboard", response_model=List[schemas.LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    entries = crud.get_leaderboard(db, limit=10)
    # Add rank
    for idx, entry in enumerate(entries, start=1):
        entry["rank"] = idx
    return entries

@router.get("/user/rank")
def get_user_rank(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    score, rank = crud.get_user_rank_and_score(db, user.id)
    return {"weekly_score": score, "rank": rank}

@router.get("/winners", response_model=List[schemas.WeeklyWinner])
def get_winners(db: Session = Depends(get_db)):
    return crud.get_weekly_winners(db)
