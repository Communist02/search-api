import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic
from pydantic import BaseModel
from build_query import build_queries_for_categories
from database import MainDatabase
import sessions
from opensearch import OpenSearchManager

opensearch = OpenSearchManager()
database = MainDatabase()


app = FastAPI()
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


@app.get('/session')
async def check_session(token: str) -> dict[str, str | bool | int]:
    session = await sessions.get_session(token[:32])
    if session:
        return {'authenticated': True, 'user_id': session['user_id']}
    raise HTTPException(status_code=401, detail='Token invalid')


@app.delete('/session')  # safe+
async def delete_session(token: str) -> bool:
    session = await sessions.get_session(token[:32])
    if session:
        await sessions.delete_session(token[:32])
        return True
    else:
        return False


@app.get('/categories')
async def get_categories(token: str) -> dict:
    session = await sessions.get_session(token[:32])
    if session:
        categories = json.loads(open('categories.json', 'r').read())[
            'categories']
        return categories
    raise HTTPException(status_code=401, detail='Token invalid')


@app.post('/search')
async def search(request: SearchRequest) -> dict:
    session = await sessions.get_session(request.token[:32])
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
    session = await sessions.get_session(request.token[:32])
    if session:
        return database.add_to_bucket(user_id=session['user_id'], document_id=request.document_id, service_id=request.service_id)
    else:
        raise HTTPException(
            status_code=401,
            detail='Token invalid'
        )


@app.get('/get_bucket')
async def get_bucket(token) -> list | None:
    session = await sessions.get_session(token[:32])
    if session:
        return database.get_bucket(user_id=session['user_id'])
    else:
        raise HTTPException(
            status_code=401,
            detail='Token invalid'
        )


@app.post('/delete_from_bucket')
async def delete_from_bucket(request: DeleteFromBucketRequest) -> list | None:
    session = await sessions.get_session(request.token[:32])
    if session:
        return database.delete_from_bucket(user_id=session['user_id'], item_id=request.item_id)
    else:
        raise HTTPException(
            status_code=401,
            detail='Token invalid'
        )


@app.post('/clear_bucket')
async def clear_bucket(request: ClearBucketRequest):
    session = await sessions.get_session(request.token[:32])
    if session:
        database.clear_bucket(user_id=session['user_id'])
    else:
        raise HTTPException(
            status_code=401,
            detail='Token invalid'
        )
