from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List
import os
from datetime import datetime

import crud, schemas, models
from database import get_db
from auth import verify_admin

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin API endpoints protected by HTTP Basic
@router.get("/users", response_model=List[schemas.User])
def get_users(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return db.query(models.User).all()

@router.get("/events", response_model=List[schemas.Event])
def admin_get_events(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return crud.get_all_events(db)

@router.post("/events", response_model=schemas.Event)
def admin_create_event(event: schemas.EventCreate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return crud.create_event(db, event)

@router.put("/events/{event_id}", response_model=schemas.Event)
def admin_update_event(event_id: int, event_update: schemas.EventUpdate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    updated = crud.update_event(db, event_id, event_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Event not found or not active")
    return updated

@router.post("/events/{event_id}/resolve")
def admin_resolve_event(event_id: int, winning_outcome: str, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    if winning_outcome not in ('A', 'B'):
        raise HTTPException(status_code=400, detail="Invalid outcome")
    event = crud.resolve_event(db, event_id, winning_outcome)
    if not event:
        raise HTTPException(status_code=400, detail="Event cannot be resolved")
    return {"message": "Event resolved"}

@router.post("/week/finish")
def admin_finish_week(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    winner = crud.determine_weekly_winner(db)
    if not winner:
        return {"message": "No winner found"}
    return {"message": f"Week finished, winner user_id={winner.winner_user_id}"}

@router.get("/winners", response_model=List[schemas.WeeklyWinner])
def admin_get_winners(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return crud.get_weekly_winners(db)
