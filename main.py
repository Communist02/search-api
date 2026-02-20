from contextlib import asynccontextmanager
import json
import secrets
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Annotated
from build_query import build_queries_for_categories
import config
import httpx
from database import MainDatabase
from sessions import WebSessionsBase
from opensearch import OpenSearchManager

web_sessions = WebSessionsBase()
opensearch = OpenSearchManager()
database = MainDatabase()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация при запуске
    await web_sessions.initialize()
    yield
    # Завершение при остановке
    await web_sessions.close()

app = FastAPI(lifespan=lifespan)
security = HTTPBasic()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_credentials=True,
    allow_headers=["*"]
)


class SearchRequest(BaseModel):
    text: str
    token: str
    filters: dict
    categories: list[str]


class AddToBucketRequest(BaseModel):
    document_id: str
    token: str
    service_id: str


class DeleteFromBucketRequest(BaseModel):
    token: str
    item_id: int

class ClearBucketRequest(BaseModel):
    token: str


@app.get('/auth')  # safe+ logs+
async def auth(credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> dict[str, int | str | bool]:
    username = credentials.username.strip('/')
    if username.find('/') == -1:
        org = 'default'
    else:
        username, org = credentials.username.split(
            '/')[0], credentials.username.split('/')[-1]
    if org == 'default' or org == '':
        credentials.username = username
    async with httpx.AsyncClient(verify=not config.debug_mode) as client:
        response = await client.post(
            f'{config.auth_api_url}/login?org={org}',
            auth=(username, credentials.password)
        )
    if response.status_code == 200:
        jwt_token = response.json()
    else:
        raise HTTPException(
            status_code=401,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Basic'},
        )
    token = secrets.token_urlsafe(24)[:32]
    await web_sessions.add_session(token, jwt_token, username, org)
    return {
        'token': token,
        'username': username
    }


@app.get('/session')
async def check(token: str) -> dict[str, str | bool]:
    user = await web_sessions.get_username_and_org(token)
    if user:
        username, org = user
        return {'authenticated': True, 'username': username, 'org': org}
    raise HTTPException(status_code=401, detail='Token invalid')


@app.get('/categories')
async def get_categories(token: str) -> dict:
    user = await web_sessions.get_username_and_org(token)
    if user:
        categories = json.loads(open('categories.json', 'r').read())[
            'categories']
        return categories
    raise HTTPException(status_code=401, detail='Token invalid')


@app.post('/search')
async def search(request: SearchRequest) -> dict:
    session = await web_sessions.get_session(request.token[:32])
    if session:
        queries = build_queries_for_categories(
            categories=request.categories, text=request.text, filters=request.filters)
        documents = await opensearch.search_documents(queries=queries, jwt_token=session['jwt_token'])
        return documents
    else:
        raise HTTPException(
            status_code=401,
            detail='Token invalid'
        )


@app.post('/add_to_bucket')
async def add_to_bucket(request: AddToBucketRequest) -> int | None:
    session = await web_sessions.get_session(request.token[:32])
    if session:
        user_id = database.get_user_id(session['username'])
        if user_id:
            return database.add_to_bucket(user_id=user_id, document_id=request.document_id, service_id=request.service_id)
    else:
        raise HTTPException(
            status_code=401,
            detail='Token invalid'
        )


@app.get('/get_bucket')
async def get_bucket(token) -> list | None:
    session = await web_sessions.get_session(token[:32])
    if session:
        user_id = database.get_user_id(session['username'])
        if user_id:
            return database.get_bucket(user_id=user_id)
    else:
        raise HTTPException(
            status_code=401,
            detail='Token invalid'
        )


@app.post('/delete_from_bucket')
async def delete_from_bucket(request: DeleteFromBucketRequest) -> list | None:
    session = await web_sessions.get_session(request.token[:32])
    if session:
        user_id = database.get_user_id(session['username'])
        if user_id:
            return database.delete_from_bucket(user_id=user_id, item_id=request.item_id)
    else:
        raise HTTPException(
            status_code=401,
            detail='Token invalid'
        )


@app.post('/clear_bucket')
async def clear_bucket(request: ClearBucketRequest):
    session = await web_sessions.get_session(request.token[:32])
    if session:
        user_id = database.get_user_id(session['username'])
        if user_id:
           database.clear_bucket(user_id=user_id)
    else:
        raise HTTPException(
            status_code=401,
            detail='Token invalid'
        )
