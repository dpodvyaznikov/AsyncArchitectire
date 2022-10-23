from datetime import datetime
from sqlalchemy.orm import Session

from . import models, schemas

def cur_date():
    return datetime.now().strftime("%d.%m.%Y")

def create_user(db: Session, user: schemas.User): 
    user = models.User(public_id=user.public_id, role=user.role, is_active=user.is_active)
    db.add(user)
    db.commit()

def update_user(db: Session, user: schemas.User):
    db_user = db.query(models.User).filter(models.User.public_id == user.public_id).first()
    for k, v in user.dict().items():
        setattr(db_user, k, v)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_balance(db: Session, public_id, transaction):
    user = db.query(models.User).filter(models.User.public_id==public_id).first()
    user.balance = user.balance + transaction
    db.commit()
    db.refresh(user)

def create_transaction(db: Session, user_public_id, transaction, transaction_type, comment):
    db_transaction = models.Transaction(user_public_id=user_public_id, date=cur_date(),
                                        transaction_type=transaction_type,
                                        transaction=transaction, comment=comment)
    db.add(db_transaction)
    db.commit()
    update_balance(db, db_transaction.user_public_id, db_transaction.transaction)

def create_task(db: Session, task: schemas.Task, cost, reward):
    db_task = models.Task(public_id=task.public_id, title=task.title, cost=cost,
                          reward=reward, assignee=task.assignee)
    db.add(db_task)
    db.commit()
    create_transaction(db, db_task.assignee, db_task.cost, 'TaskAssigned', db_task.title)

def finish_task(db: Session, public_id, status):
    db_task = db.query(models.Task).filter(models.Task.public_id==public_id).first()
    db_task.status = status
    db.commit()
    db.refresh(db_task)
    create_transaction(db, db_task.assignee, db_task.reward, 'TaskFinished', db_task.title)
    db.commit()

def reassign_task(db: Session, public_id, assignee):
    db_task = db.query(models.Task).filter(models.Task.public_id==public_id).first()
    db_task.assignee = assignee
    db.commit()
    db.refresh(db_task)
    create_transaction(db, db_task.assignee, db_task.cost, 'TaskAssigned', db_task.title)
    db.commit()

def read_user_balance(db: Session, user_public_id):
    db_user = (db.query(models.User)
             .filter(models.User.public_id==user_public_id)
             .first())
    return db_user.balance

def read_user_log(db: Session, user_public_id):
    today = cur_date()
    log = (db.query(models.Transaction)
             .filter(models.Transaction.date==today).filter(models.Transaction.user_public_id==user_public_id)
             .distinct().all())
    return log

def read_log(db: Session, date=None):
    date = cur_date() if date is None else date
    logs = (db.query(models.Transaction)
             .filter(models.Transaction.date==date and models.Transaction.transaction_type!='BalancePaid')
             .distinct().all())
    return logs