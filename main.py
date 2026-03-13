import json
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic
from pydantic import BaseModel
from build_query import build_queries_for_categories
from database import MainDatabase
import sessions
from opensearch import OpenSearchManager
from validate import get_current_user

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
    filters: dict
    categories: list[str]


class AddToBucketRequest(BaseModel):
    document_id: str
    service_id: str


class DeleteFromBucketRequest(BaseModel):
    item_id: int


@app.get('/session')
async def check_session(session: dict = Depends(get_current_user)) -> dict[str, str | bool | int]:
    return {'authenticated': True, 'user_id': session['user_id']}


@app.delete('/session')  # safe+
async def delete_session(token: str) -> bool:
    session = await sessions.get_session(token[:32])
    if session:
        await sessions.delete_session(token[:32])
        return True
    else:
        return False


@app.get('/categories')
async def get_categories(session: dict = Depends(get_current_user)) -> dict:
    categories = json.loads(open('categories.json', 'r').read())['categories']
    return categories


@app.post('/search')
async def search(request: SearchRequest, session: dict = Depends(get_current_user)) -> dict:
    queries = build_queries_for_categories(
        categories=request.categories, text=request.text, filters=request.filters)
    documents = await opensearch.search_documents(queries=queries, jwt_token=session['jwt_token'])
    return documents


@app.post('/add_to_bucket')
async def add_to_bucket(request: AddToBucketRequest, session: dict = Depends(get_current_user)) -> int | None:
    print(session['user_id'])
    return database.add_to_bucket(user_id=session['user_id'], document_id=request.document_id, service_id=request.service_id)


@app.get('/get_bucket')
async def get_bucket(session: dict = Depends(get_current_user)) -> list | None:
    return database.get_bucket(user_id=session['user_id'])


@app.post('/delete_from_bucket')
async def delete_from_bucket(request: DeleteFromBucketRequest, session: dict = Depends(get_current_user)) -> list | None:
    return database.delete_from_bucket(user_id=session['user_id'], item_id=request.item_id)


@app.post('/clear_bucket')
async def clear_bucket(session: dict = Depends(get_current_user)):
    database.clear_bucket(user_id=session['user_id'])
