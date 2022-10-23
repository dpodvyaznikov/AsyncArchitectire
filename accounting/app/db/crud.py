import numpy as np
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from . import models, schemas

def create_user(db: Session, public_id):
    user = models.User(public_id=public_id)
    db.add(user)
    db.commit()

def update_user(db: Session, public_id, transaction):
    user = db.query(models.User).filter(models.User.public_id==public_id).first()
    user.balance = user.balance + transaction
    db.commit()
    db.refresh(user)

def create_transaction(db: Session, public_id, transaction, comment):
    transaction = models.Transaction(public_id=public_id, transaction=transaction, comment=comment)
    db.add(transaction)
    db.commit()
    update_user(db, public_id, transaction)

def create_task(db: Session, original_id, title, cost, reward, assignee):
    db_task = models.Task(original_id=original_id, title=title, cost=cost, reward=reward, assignee=assignee)
    db.add(db_task)
    db.commit()
    create_transaction(db, assignee, cost, title)

def finish_task(db: Session, original_id):
    task = db.query(models.Task).filter(models.Task.original_id==original_id).first()
    create_transaction(db, task.assignee, task.reward, task.title)
    db.delete(task)
    db.commit()


