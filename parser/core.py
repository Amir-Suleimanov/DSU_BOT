import os

from dotenv import load_dotenv
import aiohttp
import pytz
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError


class ParsingConfig:
    tz = pytz.timezone("Europe/Moscow")
    user_agent = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        )
    }


load_dotenv()
SSL_STATUS = os.getenv("SSL_STATUS", "true").lower() in {"1", "true", "yes", "on"}
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))


class SiteUnavailableError(Exception):
    pass


async def make_request(
    url: str,
    cookie: str | None = None,
    params: dict | None = None,
    response_type: str | None = None,
):
    if cookie:
        cookie = {".AspNetCore.Cookies": cookie}
    try:
        async with aiohttp.ClientSession(
            headers=ParsingConfig.user_agent,
            cookies=cookie,
        ) as session:
            async with session.get(
                url=url,
                params=params,
                timeout=REQUEST_TIMEOUT,
                ssl=SSL_STATUS,
            ) as response:
                if response_type == "json":
                    return await response.json()
                return await response.text()

    except (TimeoutError, ClientConnectorError) as err:
        raise SiteUnavailableError from err
    except Exception as err:
        raise err
