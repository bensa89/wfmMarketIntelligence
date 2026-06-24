import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.app_setting import AppSetting
from app.schemas.settings_admin import AppSettingRead, AppSettingUpdate
from app.settings_overrides import OVERRIDABLE_FIELDS, apply_override, default_value, reset_override

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[AppSettingRead])
def list_settings(db: Session = Depends(get_db)):
    overridden_keys = {row.key for row in db.query(AppSetting.key).all()}
    return [
        AppSettingRead(
            key=key,
            current_value=str(getattr(settings, key)),
            default_value=str(default_value(key)),
            is_override=key in overridden_keys,
        )
        for key in OVERRIDABLE_FIELDS
    ]


@router.put("/{key}", response_model=AppSettingRead)
def update_setting(key: str, payload: AppSettingUpdate, db: Session = Depends(get_db)):
    if key not in OVERRIDABLE_FIELDS:
        raise HTTPException(status_code=404, detail=f"Unknown setting: {key}")
    try:
        value = apply_override(key, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row is None:
        row = AppSetting(key=key, value=str(value))
        db.add(row)
    else:
        row.value = str(value)
    db.commit()
    logger.info("Setting override applied: %s=%s", key, value)

    return AppSettingRead(
        key=key, current_value=str(value), default_value=str(default_value(key)), is_override=True,
    )


@router.delete("/{key}", response_model=AppSettingRead)
def delete_setting(key: str, db: Session = Depends(get_db)):
    if key not in OVERRIDABLE_FIELDS:
        raise HTTPException(status_code=404, detail=f"Unknown setting: {key}")
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row is not None:
        db.delete(row)
        db.commit()
    value = reset_override(key)
    logger.info("Setting override reset: %s -> %s", key, value)
    return AppSettingRead(
        key=key, current_value=str(value), default_value=str(default_value(key)), is_override=False,
    )
