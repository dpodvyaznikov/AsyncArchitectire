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
from uuid import uuid4
from schema_registry import validate

from sqlalchemy.orm import Session
from db import crud, models, schemas, SessionLocal, engine

from routing import AccountingPika

models.Base.metadata.create_all(bind=engine)


class AccountingApp(FastAPI):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.broker = AccountingPika()

    @classmethod
    def log_incoming_message(cls, message: dict):
        print(f'Here we got incoming message {message}')

app = AccountingApp()

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




############ Dirty hack to emulate dependency injection in app startup event ################

@app.on_event('startup')
async def startup():
    loop = asyncio.get_running_loop()
    task = loop.create_task(app.broker.consume(loop))
    await task

if __name__ == '__main__':
    uvicorn.run('main:app', host="0.0.0.0", port=8081, workers=1,
                reload=True, debug=True, log_level="debug")
