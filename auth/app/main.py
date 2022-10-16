from dataclasses import fields
from typing import List

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
import uvicorn

from sqlalchemy.orm import Session
from db import crud, models, schemas, SessionLocal, engine

from routing import AuthPika

from uuid import uuid4
import json
from schema_registry import validate

models.Base.metadata.create_all(bind=engine)


app = FastAPI()

broker = AuthPika()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LoginCredentials(BaseModel):
    email: str
    password: str


class Settings(BaseModel):
    authjwt_secret_key: str = "secret"
    # Configure application to store and get JWT from cookies
    authjwt_token_location: set = {"cookies"}
    # Disable CSRF Protection for this example. default is True
    authjwt_cookie_csrf_protect: bool = False

@AuthJWT.load_config
def get_config():
    return Settings()


############# OAuth2 stuff ######################

@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

@app.post('/login')
def login(credentials: LoginCredentials, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    db_user = crud.get_user_by_email(db, email=credentials.email)
    if not db_user or (crud.hash_password(credentials.password) != db_user.hashed_password): # Damn, thats insecure
        raise HTTPException(status_code=401,detail="Bad username or password")

    # Create the tokens and passing to set_access_cookies or set_refresh_cookies
    access_token = Authorize.create_access_token(subject=db_user.public_id)
    refresh_token = Authorize.create_refresh_token(subject=db_user.public_id)

    # Set the JWT cookies in the response
    Authorize.set_access_cookies(access_token)
    Authorize.set_refresh_cookies(refresh_token)
    return {"msg":"Successfully login"}

@app.post('/refresh')
def refresh(Authorize: AuthJWT = Depends()):
    Authorize.jwt_refresh_token_required()

    current_user = Authorize.get_jwt_subject()
    new_access_token = Authorize.create_access_token(subject=current_user)
    # Set the JWT cookies in the response
    Authorize.set_access_cookies(new_access_token)
    return {"msg":"The token has been refresh"}

@app.delete('/logout')
def logout(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()

    Authorize.unset_jwt_cookies()
    return {"msg":"Successfully logout"}

@app.get('/protected', response_model=schemas.User)
def protected(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()

    public_id = Authorize.get_jwt_subject()
    db_user = crud.get_user_by_public_id(db, public_id=public_id)
    return db_user

@app.get('/user_info/', response_model=schemas.User)
def protected(user_id: str, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()
    public_id = Authorize.get_jwt_subject()
    db_user = crud.get_user_by_public_id(db, public_id=public_id)
    return db_user

@app.get('/user_info/{user_id}', response_model=schemas.User)
def protected(user_id: str, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()
    print(f'from userinfo: {user_id}')
    db_user = crud.get_user_by_public_id(db, public_id=user_id)
    return db_user

################## CRUD Stuff ########################

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), Authorize: AuthJWT = Depends(), broker: AuthPika = Depends()):
    Authorize.jwt_required()
    current_user_id = Authorize.get_jwt_subject()
    current_user = crud.get_user_by_public_id(db, public_id=current_user_id)
    if current_user.role != 'admin':
        raise HTTPException(status_code=401, detail="Only admin can add or modify users")

    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = crud.create_user(db=db, user=user)
    message = {
        "title": "Account.Created.v1",
        "properties": {
            "event_id": str(uuid4()),
            "event_version": 1,
            "producer": "auth.shuffle_tasks",
            "data": {
                "public_id": new_user.public_id
            }
        }
    }
    validate.validate_event(message, './schema_registry/auth', 'account.created.json')
    print(message)
    broker.send_event(routing_key='account.created', message=json.dumps(message))
    print(new_user.public_id)
    return new_user

@app.post("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: str, fields: schemas.UserUpdate, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_user_id = Authorize.get_jwt_subject()
    current_user = crud.get_user_by_public_id(db, public_id=current_user_id)
    print(current_user.role)
    if current_user.role != 'admin':
        raise HTTPException(status_code=401, detail="Only admin can add or modify users")

    fields = {k:v for k,v in fields.dict().items() if v is not None}
    updated_user = crud.update_user(db, user_id, fields)
    message = {
        "title": "Account.Updated.v1",
        "properties": {
            "event_id": str(uuid4()),
            "event_version": 1,
            "producer": "auth.shuffle_tasks",
            "data": {
                "public_id": updated_user.public_id
            }
        }
    }
    validate.validate_event(message, './schema_registry/auth', 'account.updated.json')
    print(message)
    broker.send_event(routing_key='account.updated', message=json.dumps(message))
    return updated_user

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

############ Dirty hack to emulate dependency injection in app startup event ################

import contextlib
get_db_wrapper = contextlib.contextmanager(get_db)

@app.on_event("startup")
def startup_event():
    with get_db_wrapper() as db:
        db_user = crud.get_user(db, user_id=1)
        if db_user is None:
            admin = schemas.UserCreate(email='adminest@admin.com', password='sesurity', role='admin')
            return crud.create_user(db=db, user=admin)

if __name__ == '__main__':
    uvicorn.run('main:app', host="0.0.0.0", port=8080, workers=1,
                reload=True, debug=True, log_level="debug")
