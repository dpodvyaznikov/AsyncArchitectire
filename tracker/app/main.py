from email.message import EmailMessage
from http import client
from importlib.resources import contents
from pyexpat.errors import messages
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
# from fastapi_jwt_auth import AuthJWT
# from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
import uvicorn
import httpx
import asyncio
import json
import numpy as np
from uuid import uuid4
from schema_registry import validate

from sqlalchemy.orm import Session
from db import crud, models, schemas, SessionLocal, engine

from routing import TrackerPika

models.Base.metadata.create_all(bind=engine)


class TrackerApp(FastAPI):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.broker = TrackerPika()

    @classmethod
    def log_incoming_message(cls, message: dict):
        print(f'Here we got incoming message {message}')

app = TrackerApp()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request):
    try:
        cookie_authorization: str = request.cookies.get("access_token_cookie")
        cookies = httpx.Cookies()
        cookies.set('access_token_cookie', cookie_authorization)
        with httpx.AsyncClient() as client:
            user_info = client.get('auth:8080/user_info', cookies=cookies)
        print(user_info)
    except Exception as e:
        response = RedirectResponse(url='auth:8080/docs#/default/login_login_post')
        return response
    return user_info

@app.post("/task/")
def create_task(task: schemas.TaskCreate, request: Request, db: Session = Depends(get_db)):#, Authorize: AuthJWT = Depends(),):
    _ = get_current_user(request)
    new_task = crud.create_task(db=db, task=task)
    message = {
        "title": "Task.Created.v2",
        "properties": {
            "event_id": str(uuid4()),
            "event_version": 1,
            "producer": "tracker.create_task",
            "data": {
                "public_id": new_task.public_id,
                "title": new_task.title,
                "jira_id": new_task.jira_id,
                "description": new_task.description,
                "status": new_task.status,
                "assignee": new_task.assignee
            }
        }
    }
    print(message)
    validate.validate_event(message, './schema_registry/tracker/task_created', 'v2.json')
    request.app.broker.send_event(routing_key='task.created', message=json.dumps(message))
    return new_task

@app.post("/task/shuffle")
def shuffle_tasks(request: Request, db: Session = Depends(get_db)):#, Authorize: AuthJWT = Depends(),):
    user_info = get_current_user(request)
    if user_info['role'] not in ('admin', 'manager'):
        return JSONResponse(status_code=403, content={'message': 'Only Admins and Managers can shuffle' })

    tasks = db.query(models.Task).filter(models.Task.status != 'finished').distinct()
    assignees = np.random.choice(db.query(models.User).filter(models.User.role != 'manager').distinct(), len(tasks))
    for task, assignee in zip(tasks, assignees):
        setattr(task, 'assignee', assignee.public_id)
        db.commit()
        message = {
            "title": "Task.Reassigned.v1",
            "properties": {
                "event_id": str(uuid4()),
                "event_version": 1,
                "producer": "tracker.shuffle_tasks",
                "data": {
                    "public_id": task.public_id,
                    "assignee": assignee.public_id
                }
            }
        }
        validate.validate_event(message, './schema_registry/tracker/task_reassigned', 'v1.json')
        request.app.broker.send_event(routing_key='task.shuffled', message=json.dumps(message))
    return JSONResponse(status_code=200, content={'message': f'Tasks have been shuffled'})


@app.get("/task/")
def create_task(request: Request, db: Session = Depends(get_db)):#, Authorize: AuthJWT = Depends(),):
    user_info = get_current_user(request)
    tasks = crud.read_user_tasks(db=db, user_id=user_info.public_id)
    return tasks

@app.post("/task/finish/{task_id}")
def finish_task(task_id: int, request: Request, db: Session = Depends(get_db)):#, Authorize: AuthJWT = Depends(),):
    user_info = get_current_user(request)
    task = db.query(models.Task).filter(models.Task.id==task_id).first()
    if user_info.public_id != task.assignee:
        return JSONResponse(status_code=403, content={'message': 'Only Assignee can finish own tasks' })
    db_task = crud.finish_task(db=db, task_id=task_id)
    message = {
        "title": "Task.Finished.v1",
        "properties": {
            "event_id": str(uuid4()),
            "event_version": 1,
            "producer": "tracker.finish_task",
            "data": {
                "public_id": db_task.public_id,
                "status": db_task.status
            }
        }
    }
    validate.validate_event(message, './schema_registry/tracker/task_finished', 'v1.json')
    request.app.broker.send_event(routing_key='task.finished', message=json.dumps(message))
    return JSONResponse(status_code=200, content={'message': f'Task {task.title} has been finished'})


############ Dirty hack to emulate dependency injection in app startup event ################

@app.on_event('startup')
async def startup():
    loop = asyncio.get_running_loop()
    task = loop.create_task(app.broker.consume(loop))
    await task

if __name__ == '__main__':
    uvicorn.run('main:app', host="0.0.0.0", port=8081, workers=1,
                reload=True, debug=True, log_level="debug")
