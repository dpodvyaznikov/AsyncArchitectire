from uuid import uuid4
import numpy as np
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from . import models, schemas


def create_user(db: Session, user: schemas.User):
    db_user = models.User(public_id=user.public_id, role=user.role, is_active=user.is_active)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user: schemas.User):
    db_user = db.query(models.User).filter(models.User.public_id == user.public_id).first()
    for k, v in user.dict().items():
        setattr(db_user, k, v)
    db.commit()
    db.refresh(db_user)
    return db_user
 
def create_task(db: Session, task: schemas.TaskCreate):
    assignee = db.query(models.User).filter(models.User.role != 'manager').order_by(func.random()).first()
    db_task = models.Task(public_id=str(uuid4()), title=task.title, status=task.status, jira_id=task.jira_id,
                          description=task.description, assignee=assignee.public_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def read_user_tasks(db: Session, user_id: str):
    return db.query(models.Task).filter(models.Task.assignee==user_id).distinct().all()

def finish_task(db: Session, task_id: int):
    db_task = db.query(models.Task).filter(models.Task.public_id==task_id).first()
    db_task.status = 'finished'
    db.commit()
    db.refresh(db_task)
    return db_task
