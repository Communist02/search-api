import httpx
from config import config


async def get_session(token: str) -> dict | None:
    async with httpx.AsyncClient(verify=not config.debug_mode) as client:
        response = await client.get(
            f'{config.auth_api_url}/service_session',
            headers={"token": token},
        )

    if response.status_code == 200:
        session = response.json()
        return session


async def delete_session(token: str) -> None:
    async with httpx.AsyncClient(verify=not config.debug_mode) as client:
        response = await client.delete(
            f'{config.auth_api_url}/session',
            headers={"token": token},
        )
