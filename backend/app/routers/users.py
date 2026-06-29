from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_user, require_admin, hash_password, _verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserRead, UserCreate, UserUpdate, PasswordChange, MeResponse

router = APIRouter()


@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/password", response_model=MeResponse)
def change_own_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("", response_model=List[UserRead], dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserRead, dependencies=[Depends(require_admin)])
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    active_admins = db.query(User).filter(User.role == UserRole.admin, User.is_active == True).count()
    if user.role == UserRole.admin and active_admins <= 1:
        raise HTTPException(status_code=409, detail="Cannot delete the last active admin")
    db.delete(user)
    db.commit()
