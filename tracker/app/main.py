from http import client
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
# from fastapi_jwt_auth import AuthJWT
# from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
import uvicorn
import httpx
import asyncio

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



@app.post("/task/", response_model=schemas.User)
def create_task(task: schemas.TaskCreate, request: Request, db: Session = Depends(get_db)):#, Authorize: AuthJWT = Depends(),):
    _ = get_current_user(request)
    new_task = crud.create_task(db=db, task=task)
    request.app.broker.send_event(routing_key='task.created', message=new_task.public_id)
    return new_task

# @app.post("/users/{user_id}", response_model=schemas.User)
# def update_user(user_id: str, fields: schemas.UserUpdate, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
#     Authorize.jwt_required()
#     current_user_id = Authorize.get_jwt_subject()
#     current_user = crud.get_user_by_public_id(db, public_id=current_user_id)
#     if current_user.role != 'admin':
#         raise HTTPException(status_code=401, detail="Only admin can add or modify users")

#     fields = {k:v for k,v in fields.dict().items() if v is not None}
#     updated_user = crud.update_user(db, user_id, fields)
#     broker.send_event(routing_key='account.updated', message=updated_user.public_id)
#     return updated_user

# @app.get("/users/{user_id}", response_model=schemas.User)
# def read_user(user_id: int, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
#     Authorize.jwt_required()
#     db_user = crud.get_user(db, user_id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user

############ Dirty hack to emulate dependency injection in app startup event ################

@app.on_event('startup')
async def startup():
    loop = asyncio.get_running_loop()
    task = loop.create_task(app.broker.consume(loop))
    await task

if __name__ == '__main__':
    uvicorn.run('main:app', host="0.0.0.0", port=8081, workers=1,
                reload=True, debug=True, log_level="debug")
