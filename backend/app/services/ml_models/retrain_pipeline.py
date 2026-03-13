"""
Retrain pipeline - Load settled data, retrain ML models, persist and record model version.
Intended for weekly cron or manual POST /admin/ml/retrain.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict

from ...database import get_db
from ...models.app_settings import AppSettings


def run_retrain(min_samples: int = 50) -> Dict[str, Any]:
    """
    Run full retrain: prepare data from DB, train confidence and line models, save to disk,
    and update AppSettings with current model_version (timestamp).
    """
    db = next(get_db())
    try:
        from .trainer import ModelTrainer
        trainer = ModelTrainer(use_xgboost=True)
        result = trainer.train_models(db, min_samples=min_samples)
        if not result.get("success"):
            return result
        version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        existing = db.query(AppSettings).filter(AppSettings.key == "ml_model_version").first()
        if existing:
            existing.value = version
            existing.updated_at = datetime.utcnow()
        else:
            db.add(AppSettings(key="ml_model_version", value=version, description="Last ML retrain timestamp"))
        db.commit()
        result["model_version"] = version
        return result
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()
