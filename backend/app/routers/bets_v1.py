"""
Bets API Router - Track user bets and system accuracy
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import date, datetime
from ..database import get_db
from ..models.user_bets import UserBet

router = APIRouter(prefix="/api/v1/bets", tags=["bets_v1"])


class CreateBetRequest(BaseModel):
    player_id: int
    player_name: str
    prop_type: str  # PTS, REB, AST, 3PM, PRA
    line_value: float
    direction: str  # 'over' or 'under'
    game_date: str  # YYYY-MM-DD format
    system_confidence: Optional[float] = None
    system_fair_line: Optional[float] = None
    system_suggestion: Optional[str] = None
    amount: Optional[float] = None
    odds: Optional[str] = None
    notes: Optional[str] = None


class UpdateBetRequest(BaseModel):
    result: Optional[str] = None  # 'won', 'lost', 'push', 'void'
    actual_value: Optional[float] = None
    payout: Optional[float] = None
    notes: Optional[str] = None


class BetResponse(BaseModel):
    id: int
    player_id: int
    player_name: str
    prop_type: str
    line_value: float
    direction: str
    game_date: str
    system_confidence: Optional[float] = None
    system_fair_line: Optional[float] = None
    system_suggestion: Optional[str] = None
    amount: Optional[float] = None
    odds: Optional[str] = None
    notes: Optional[str] = None
    result: str
    actual_value: Optional[float] = None
    payout: Optional[float] = None
    created_at: str
    updated_at: str
    settled_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("", response_model=BetResponse)
def create_bet(bet: CreateBetRequest, db: Session = Depends(get_db)):
    """Record a new bet"""
    try:
        game_date_obj = datetime.strptime(bet.game_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid game_date format. Use YYYY-MM-DD")
    
    db_bet = UserBet(
        player_id=bet.player_id,
        player_name=bet.player_name,
        prop_type=bet.prop_type.upper(),
        line_value=bet.line_value,
        direction=bet.direction.lower(),
        game_date=game_date_obj,
        system_confidence=bet.system_confidence,
        system_fair_line=bet.system_fair_line,
        system_suggestion=bet.system_suggestion,
        amount=bet.amount,
        odds=bet.odds,
        notes=bet.notes,
        result="pending"
    )
    
    db.add(db_bet)
    db.commit()
    db.refresh(db_bet)
    
    return BetResponse(
        id=db_bet.id,
        player_id=db_bet.player_id,
        player_name=db_bet.player_name,
        prop_type=db_bet.prop_type,
        line_value=db_bet.line_value,
        direction=db_bet.direction,
        game_date=db_bet.game_date.isoformat(),
        system_confidence=db_bet.system_confidence,
        system_fair_line=db_bet.system_fair_line,
        system_suggestion=db_bet.system_suggestion,
        amount=db_bet.amount,
        odds=db_bet.odds,
        notes=db_bet.notes,
        result=db_bet.result,
        actual_value=db_bet.actual_value,
        payout=db_bet.payout,
        created_at=db_bet.created_at.isoformat() if db_bet.created_at else "",
        updated_at=db_bet.updated_at.isoformat() if db_bet.updated_at else "",
        settled_at=db_bet.settled_at.isoformat() if db_bet.settled_at else None
    )


@router.patch("/{bet_id}", response_model=BetResponse)
def update_bet(bet_id: int, update: UpdateBetRequest, db: Session = Depends(get_db)):
    """Update a bet (typically to mark as won/lost)"""
    db_bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
    if not db_bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    if update.result:
        if update.result not in ['won', 'lost', 'push', 'void', 'pending']:
            raise HTTPException(status_code=400, detail="Invalid result. Must be: won, lost, push, void, or pending")
        db_bet.result = update.result
        if update.result in ['won', 'lost', 'push', 'void']:
            db_bet.settled_at = datetime.utcnow()
    
    if update.actual_value is not None:
        db_bet.actual_value = update.actual_value
    
    if update.payout is not None:
        db_bet.payout = update.payout
    
    if update.notes is not None:
        db_bet.notes = update.notes
    
    db.commit()
    db.refresh(db_bet)
    
    return BetResponse(
        id=db_bet.id,
        player_id=db_bet.player_id,
        player_name=db_bet.player_name,
        prop_type=db_bet.prop_type,
        line_value=db_bet.line_value,
        direction=db_bet.direction,
        game_date=db_bet.game_date.isoformat(),
        system_confidence=db_bet.system_confidence,
        system_fair_line=db_bet.system_fair_line,
        system_suggestion=db_bet.system_suggestion,
        amount=db_bet.amount,
        odds=db_bet.odds,
        notes=db_bet.notes,
        result=db_bet.result,
        actual_value=db_bet.actual_value,
        payout=db_bet.payout,
        created_at=db_bet.created_at.isoformat() if db_bet.created_at else "",
        updated_at=db_bet.updated_at.isoformat() if db_bet.updated_at else "",
        settled_at=db_bet.settled_at.isoformat() if db_bet.settled_at else None
    )


@router.get("", response_model=List[BetResponse])
def list_bets(
    result: Optional[str] = None,
    player_id: Optional[int] = None,
    prop_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all bets with optional filters"""
    query = db.query(UserBet)
    
    if result:
        query = query.filter(UserBet.result == result.lower())
    
    if player_id:
        query = query.filter(UserBet.player_id == player_id)
    
    if prop_type:
        query = query.filter(UserBet.prop_type == prop_type.upper())
    
    bets = query.order_by(UserBet.created_at.desc()).limit(limit).all()
    
    return [
        BetResponse(
            id=bet.id,
            player_id=bet.player_id,
            player_name=bet.player_name,
            prop_type=bet.prop_type,
            line_value=bet.line_value,
            direction=bet.direction,
            game_date=bet.game_date.isoformat(),
            system_confidence=bet.system_confidence,
            system_fair_line=bet.system_fair_line,
            system_suggestion=bet.system_suggestion,
            amount=bet.amount,
            odds=bet.odds,
            notes=bet.notes,
            result=bet.result,
            actual_value=bet.actual_value,
            payout=bet.payout,
            created_at=bet.created_at.isoformat() if bet.created_at else "",
            updated_at=bet.updated_at.isoformat() if bet.updated_at else "",
            settled_at=bet.settled_at.isoformat() if bet.settled_at else None
        )
        for bet in bets
    ]


@router.get("/stats", response_model=Dict)
def get_bet_stats(db: Session = Depends(get_db)):
    """Get accuracy statistics for settled bets"""
    all_bets = db.query(UserBet).filter(
        UserBet.result.in_(['won', 'lost', 'push'])
    ).all()
    
    total = len(all_bets)
    won = len([b for b in all_bets if b.result == 'won'])
    lost = len([b for b in all_bets if b.result == 'lost'])
    push = len([b for b in all_bets if b.result == 'push'])
    
    win_rate = (won / total * 100) if total > 0 else 0
    
    # System accuracy (when user followed system suggestion)
    system_bets = [b for b in all_bets if b.system_suggestion and b.direction == b.system_suggestion]
    system_total = len(system_bets)
    system_won = len([b for b in system_bets if b.result == 'won'])
    system_win_rate = (system_won / system_total * 100) if system_total > 0 else 0
    
    # By prop type
    by_type = {}
    for prop_type in ['PTS', 'REB', 'AST', '3PM', 'PRA']:
        type_bets = [b for b in all_bets if b.prop_type == prop_type]
        if type_bets:
            type_won = len([b for b in type_bets if b.result == 'won'])
            by_type[prop_type] = {
                'total': len(type_bets),
                'won': type_won,
                'win_rate': (type_won / len(type_bets) * 100) if type_bets else 0
            }
    
    # By confidence level
    by_confidence = {
        'high': {'total': 0, 'won': 0},  # >= 70
        'medium': {'total': 0, 'won': 0},  # 50-69
        'low': {'total': 0, 'won': 0}  # < 50
    }
    
    for bet in all_bets:
        if bet.system_confidence is not None:
            if bet.system_confidence >= 70:
                cat = 'high'
            elif bet.system_confidence >= 50:
                cat = 'medium'
            else:
                cat = 'low'
            
            by_confidence[cat]['total'] += 1
            if bet.result == 'won':
                by_confidence[cat]['won'] += 1
    
    for cat in by_confidence:
        total_cat = by_confidence[cat]['total']
        if total_cat > 0:
            by_confidence[cat]['win_rate'] = (by_confidence[cat]['won'] / total_cat * 100)
        else:
            by_confidence[cat]['win_rate'] = 0
    
    return {
        'overall': {
            'total': total,
            'won': won,
            'lost': lost,
            'push': push,
            'win_rate': round(win_rate, 2)
        },
        'system_accuracy': {
            'total': system_total,
            'won': system_won,
            'win_rate': round(system_win_rate, 2)
        },
        'by_prop_type': by_type,
        'by_confidence': by_confidence,
        'pending': db.query(UserBet).filter(UserBet.result == 'pending').count()
    }


@router.get("/{bet_id}", response_model=BetResponse)
def get_bet(bet_id: int, db: Session = Depends(get_db)):
    """Get a specific bet by ID"""
    bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    return BetResponse(
        id=bet.id,
        player_id=bet.player_id,
        player_name=bet.player_name,
        prop_type=bet.prop_type,
        line_value=bet.line_value,
        direction=bet.direction,
        game_date=bet.game_date.isoformat(),
        system_confidence=bet.system_confidence,
        system_fair_line=bet.system_fair_line,
        system_suggestion=bet.system_suggestion,
        amount=bet.amount,
        odds=bet.odds,
        notes=bet.notes,
        result=bet.result,
        actual_value=bet.actual_value,
        payout=bet.payout,
        created_at=bet.created_at.isoformat() if bet.created_at else "",
        updated_at=bet.updated_at.isoformat() if bet.updated_at else "",
        settled_at=bet.settled_at.isoformat() if bet.settled_at else None
    )


@router.delete("/{bet_id}")
def delete_bet(bet_id: int, db: Session = Depends(get_db)):
    """Delete a bet"""
    bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    db.delete(bet)
    db.commit()
    
    return {"status": "deleted", "id": bet_id}

