"""
Parlays API Router - Track user parlay bets
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import date, datetime
from ..database import get_db
from ..models.user_parlays import UserParlay, UserParlayLeg

router = APIRouter(prefix="/api/v1/parlays", tags=["parlays_v1"])


class ParlayLegRequest(BaseModel):
    player_id: int
    player_name: str
    prop_type: str  # PTS, REB, AST, 3PM, PRA
    line_value: float
    direction: str  # 'over' or 'under'
    system_confidence: Optional[float] = None
    system_fair_line: Optional[float] = None
    system_suggestion: Optional[str] = None
    system_hit_rate: Optional[float] = None  # 0-100 (percentage) - hit rate for the chosen direction


class CreateParlayRequest(BaseModel):
    name: Optional[str] = None
    game_date: str  # YYYY-MM-DD format
    total_amount: Optional[float] = None
    total_odds: Optional[str] = None
    system_confidence: Optional[float] = None
    notes: Optional[str] = None
    legs: List[ParlayLegRequest]


class UpdateParlayRequest(BaseModel):
    result: Optional[str] = None  # 'won', 'lost', 'push', 'void'
    total_payout: Optional[float] = None
    notes: Optional[str] = None


class ParlayLegResponse(BaseModel):
    id: int
    parlay_id: int
    player_id: int
    player_name: str
    prop_type: str
    line_value: float
    direction: str
    system_confidence: Optional[float] = None
    system_fair_line: Optional[float] = None
    system_suggestion: Optional[str] = None
    system_hit_rate: Optional[float] = None  # 0-100 (percentage) - hit rate for the chosen direction
    result: str
    actual_value: Optional[float] = None
    created_at: str

    class Config:
        from_attributes = True


class ParlayResponse(BaseModel):
    id: int
    name: Optional[str] = None
    game_date: str
    total_amount: Optional[float] = None
    total_odds: Optional[str] = None
    total_payout: Optional[float] = None
    system_confidence: Optional[float] = None
    leg_count: int
    result: str
    notes: Optional[str] = None
    created_at: str
    updated_at: str
    settled_at: Optional[str] = None
    legs: List[ParlayLegResponse] = []

    class Config:
        from_attributes = True


@router.post("", response_model=ParlayResponse)
def create_parlay(parlay: CreateParlayRequest, db: Session = Depends(get_db)):
    """Create a new parlay"""
    if len(parlay.legs) < 2:
        raise HTTPException(status_code=400, detail="Parlay must have at least 2 legs")
    
    try:
        game_date_obj = datetime.strptime(parlay.game_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid game_date format. Use YYYY-MM-DD")
    
    # Calculate aggregate confidence if not provided
    system_confidence = parlay.system_confidence
    if system_confidence is None:
        confidences = [leg.system_confidence for leg in parlay.legs if leg.system_confidence is not None]
        if confidences:
            # Simple average for now (could use volume adjustment from tech spec)
            system_confidence = sum(confidences) / len(confidences)
    
    try:
        db_parlay = UserParlay(
            name=parlay.name,
            game_date=game_date_obj,
            total_amount=parlay.total_amount,
            total_odds=parlay.total_odds,
            system_confidence=system_confidence,
            leg_count=len(parlay.legs),
            notes=parlay.notes,
            result="pending"
        )
        
        db.add(db_parlay)
        db.flush()  # Get the parlay ID
        
        # Create legs
        for leg_req in parlay.legs:
            # Convert hit rate from decimal (0-1) to percentage (0-100) if needed
            hit_rate = leg_req.system_hit_rate
            if hit_rate is not None:
                # If hit rate is less than 1, assume it's a decimal and convert to percentage
                if hit_rate < 1:
                    hit_rate = hit_rate * 100
            
            db_leg = UserParlayLeg(
                parlay_id=db_parlay.id,
                player_id=leg_req.player_id,
                player_name=leg_req.player_name,
                prop_type=leg_req.prop_type.upper(),
                line_value=leg_req.line_value,
                direction=leg_req.direction.lower(),
                system_confidence=leg_req.system_confidence,
                system_fair_line=leg_req.system_fair_line,
                system_suggestion=leg_req.system_suggestion,
                system_hit_rate=hit_rate,
                result="pending"
            )
            db.add(db_leg)
        
        db.commit()
        db.refresh(db_parlay)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create parlay: {str(e)}")
    
    # Load legs for response
    legs = db.query(UserParlayLeg).filter(UserParlayLeg.parlay_id == db_parlay.id).all()
    
    return ParlayResponse(
        id=db_parlay.id,
        name=db_parlay.name,
        game_date=db_parlay.game_date.isoformat(),
        total_amount=db_parlay.total_amount,
        total_odds=db_parlay.total_odds,
        total_payout=db_parlay.total_payout,
        system_confidence=db_parlay.system_confidence,
        leg_count=db_parlay.leg_count,
        result=db_parlay.result,
        notes=db_parlay.notes,
        created_at=db_parlay.created_at.isoformat() if db_parlay.created_at else "",
        updated_at=db_parlay.updated_at.isoformat() if db_parlay.updated_at else "",
        settled_at=db_parlay.settled_at.isoformat() if db_parlay.settled_at else None,
        legs=[
            ParlayLegResponse(
                id=leg.id,
                parlay_id=leg.parlay_id,
                player_id=leg.player_id,
                player_name=leg.player_name,
                prop_type=leg.prop_type,
                line_value=leg.line_value,
                direction=leg.direction,
                system_confidence=leg.system_confidence,
                system_fair_line=leg.system_fair_line,
                system_suggestion=leg.system_suggestion,
                system_hit_rate=leg.system_hit_rate,
                result=leg.result,
                actual_value=leg.actual_value,
                created_at=leg.created_at.isoformat() if leg.created_at else ""
            )
            for leg in legs
        ]
    )


@router.get("", response_model=List[ParlayResponse])
def list_parlays(
    result: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all parlays with optional filters"""
    query = db.query(UserParlay)
    
    if result:
        query = query.filter(UserParlay.result == result.lower())
    
    parlays = query.order_by(UserParlay.created_at.desc()).limit(limit).all()
    
    result_list = []
    for parlay in parlays:
        legs = db.query(UserParlayLeg).filter(UserParlayLeg.parlay_id == parlay.id).all()
        result_list.append(
            ParlayResponse(
                id=parlay.id,
                name=parlay.name,
                game_date=parlay.game_date.isoformat(),
                total_amount=parlay.total_amount,
                total_odds=parlay.total_odds,
                total_payout=parlay.total_payout,
                system_confidence=parlay.system_confidence,
                leg_count=parlay.leg_count,
                result=parlay.result,
                notes=parlay.notes,
                created_at=parlay.created_at.isoformat() if parlay.created_at else "",
                updated_at=parlay.updated_at.isoformat() if parlay.updated_at else "",
                settled_at=parlay.settled_at.isoformat() if parlay.settled_at else None,
                legs=[
                    ParlayLegResponse(
                        id=leg.id,
                        parlay_id=leg.parlay_id,
                        player_id=leg.player_id,
                        player_name=leg.player_name,
                        prop_type=leg.prop_type,
                        line_value=leg.line_value,
                        direction=leg.direction,
                        system_confidence=leg.system_confidence,
                        system_fair_line=leg.system_fair_line,
                        system_suggestion=leg.system_suggestion,
                        result=leg.result,
                        actual_value=leg.actual_value,
                        created_at=leg.created_at.isoformat() if leg.created_at else ""
                    )
                    for leg in legs
                ]
            )
        )
    
    return result_list


@router.get("/{parlay_id}", response_model=ParlayResponse)
def get_parlay(parlay_id: int, db: Session = Depends(get_db)):
    """Get a specific parlay by ID"""
    parlay = db.query(UserParlay).filter(UserParlay.id == parlay_id).first()
    if not parlay:
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    legs = db.query(UserParlayLeg).filter(UserParlayLeg.parlay_id == parlay_id).all()
    
    return ParlayResponse(
        id=parlay.id,
        name=parlay.name,
        game_date=parlay.game_date.isoformat(),
        total_amount=parlay.total_amount,
        total_odds=parlay.total_odds,
        total_payout=parlay.total_payout,
        system_confidence=parlay.system_confidence,
        leg_count=parlay.leg_count,
        result=parlay.result,
        notes=parlay.notes,
        created_at=parlay.created_at.isoformat() if parlay.created_at else "",
        updated_at=parlay.updated_at.isoformat() if parlay.updated_at else "",
        settled_at=parlay.settled_at.isoformat() if parlay.settled_at else None,
        legs=[
            ParlayLegResponse(
                id=leg.id,
                parlay_id=leg.parlay_id,
                player_id=leg.player_id,
                player_name=leg.player_name,
                prop_type=leg.prop_type,
                line_value=leg.line_value,
                direction=leg.direction,
                system_confidence=leg.system_confidence,
                system_fair_line=leg.system_fair_line,
                system_suggestion=leg.system_suggestion,
                system_hit_rate=leg.system_hit_rate,
                result=leg.result,
                actual_value=leg.actual_value,
                created_at=leg.created_at.isoformat() if leg.created_at else ""
            )
            for leg in legs
        ]
    )


@router.patch("/{parlay_id}", response_model=ParlayResponse)
def update_parlay(parlay_id: int, update: UpdateParlayRequest, db: Session = Depends(get_db)):
    """Update a parlay (typically to mark as won/lost)"""
    parlay = db.query(UserParlay).filter(UserParlay.id == parlay_id).first()
    if not parlay:
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    if update.result:
        if update.result not in ['won', 'lost', 'push', 'void', 'pending']:
            raise HTTPException(status_code=400, detail="Invalid result. Must be: won, lost, push, void, or pending")
        parlay.result = update.result
        if update.result in ['won', 'lost', 'push', 'void']:
            parlay.settled_at = datetime.utcnow()
    
    if update.total_payout is not None:
        parlay.total_payout = update.total_payout
    
    if update.notes is not None:
        parlay.notes = update.notes
    
    db.commit()
    db.refresh(parlay)
    
    legs = db.query(UserParlayLeg).filter(UserParlayLeg.parlay_id == parlay_id).all()
    
    return ParlayResponse(
        id=parlay.id,
        name=parlay.name,
        game_date=parlay.game_date.isoformat(),
        total_amount=parlay.total_amount,
        total_odds=parlay.total_odds,
        total_payout=parlay.total_payout,
        system_confidence=parlay.system_confidence,
        leg_count=parlay.leg_count,
        result=parlay.result,
        notes=parlay.notes,
        created_at=parlay.created_at.isoformat() if parlay.created_at else "",
        updated_at=parlay.updated_at.isoformat() if parlay.updated_at else "",
        settled_at=parlay.settled_at.isoformat() if parlay.settled_at else None,
        legs=[
            ParlayLegResponse(
                id=leg.id,
                parlay_id=leg.parlay_id,
                player_id=leg.player_id,
                player_name=leg.player_name,
                prop_type=leg.prop_type,
                line_value=leg.line_value,
                direction=leg.direction,
                system_confidence=leg.system_confidence,
                system_fair_line=leg.system_fair_line,
                system_suggestion=leg.system_suggestion,
                system_hit_rate=leg.system_hit_rate,
                result=leg.result,
                actual_value=leg.actual_value,
                created_at=leg.created_at.isoformat() if leg.created_at else ""
            )
            for leg in legs
        ]
    )


@router.delete("/{parlay_id}")
def delete_parlay(parlay_id: int, db: Session = Depends(get_db)):
    """Delete a parlay"""
    parlay = db.query(UserParlay).filter(UserParlay.id == parlay_id).first()
    if not parlay:
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    db.delete(parlay)
    db.commit()
    
    return {"status": "deleted", "id": parlay_id}

