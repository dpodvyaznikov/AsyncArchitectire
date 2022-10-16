from sqlalchemy.orm import Session

from . import models, schemas

def hash_password(password):
    return password + "notreallyhashed"

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_public_id(db: Session, public_id: str):
    return db.query(models.User).filter(models.User.public_id == public_id).first()

def update_user(db: Session, public_id: str, fields: dict):
    db_user = db.query(models.User).filter(models.User.public_id == public_id).first()
    for k, v in fields.items():
        setattr(db_user, k, v)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_user(db: Session, user: schemas.UserCreate):
    fake_hashed_password = hash_password(user.password)
    db_user = models.User(email=user.email, hashed_password=fake_hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
