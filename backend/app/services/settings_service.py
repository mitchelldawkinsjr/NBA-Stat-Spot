"""
Settings Service - Manages application-wide settings
"""
from __future__ import annotations
from typing import Optional, Any
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.app_settings import AppSettings


class SettingsService:
    """Service for managing application settings"""
    
    # Default settings
    DEFAULT_SETTINGS = {
        "ai_enabled": {
            "value": "false",
            "description": "Enable AI features (ML models and LLM rationale generation)"
        }
    }
    
    @staticmethod
    def get_setting(key: str, db: Optional[Session] = None, default: Optional[str] = None) -> str:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            db: Database session (optional, will create if not provided)
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value as string
        """
        if db is None:
            from ..database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            setting = db.query(AppSettings).filter(AppSettings.key == key).first()
            
            if setting:
                return setting.value or ""
            else:
                # Return default from DEFAULT_SETTINGS or provided default
                if key in SettingsService.DEFAULT_SETTINGS:
                    return SettingsService.DEFAULT_SETTINGS[key]["value"]
                return default or ""
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def set_setting(key: str, value: str, description: Optional[str] = None, db: Optional[Session] = None) -> AppSettings:
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
            description: Optional description
            db: Database session (optional, will create if not provided)
            
        Returns:
            AppSettings object
        """
        if db is None:
            from ..database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            setting = db.query(AppSettings).filter(AppSettings.key == key).first()
            
            if setting:
                setting.value = value
                if description:
                    setting.description = description
            else:
                # Use description from DEFAULT_SETTINGS if not provided
                if not description and key in SettingsService.DEFAULT_SETTINGS:
                    description = SettingsService.DEFAULT_SETTINGS[key]["description"]
                
                setting = AppSettings(
                    key=key,
                    value=value,
                    description=description
                )
                db.add(setting)
            
            db.commit()
            db.refresh(setting)
            return setting
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def get_ai_enabled(db: Optional[Session] = None) -> bool:
        """
        Check if AI features are enabled.
        
        Args:
            db: Database session (optional)
            
        Returns:
            True if AI is enabled, False otherwise
        """
        value = SettingsService.get_setting("ai_enabled", db, "false")
        return value.lower() in ("true", "1", "yes", "on")
    
    @staticmethod
    def set_ai_enabled(enabled: bool, db: Optional[Session] = None) -> AppSettings:
        """
        Enable or disable AI features.
        
        Args:
            enabled: True to enable, False to disable
            db: Database session (optional)
            
        Returns:
            AppSettings object
        """
        return SettingsService.set_setting("ai_enabled", "true" if enabled else "false", db=db)
    
    @staticmethod
    def get_all_settings(db: Optional[Session] = None) -> dict:
        """
        Get all settings.
        
        Args:
            db: Database session (optional)
            
        Returns:
            Dictionary of all settings
        """
        if db is None:
            from ..database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            settings = db.query(AppSettings).all()
            result = {}
            for setting in settings:
                result[setting.key] = {
                    "value": setting.value,
                    "description": setting.description
                }
            return result
        finally:
            if should_close:
                db.close()

