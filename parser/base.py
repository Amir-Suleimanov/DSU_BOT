import aiohttp
from bs4 import BeautifulSoup
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError

from . import URL, ParsingConfig, SSL_STATUS, REQUEST_TIMEOUT
from .exeptions import SiteUnavailableError, AuthenticationError, InvalidResponseError


async def main_page(cookie: str) -> list[dict]:
    """
    Возвращает базовую информацию о студенте со страницы https://studstat.dgu.ru/
    Формат: список пар {"label": "...", "value": "..."} в исходном порядке.
    """
    try:
        async with aiohttp.ClientSession(
            headers=ParsingConfig.user_agent,
            cookies={".AspNetCore.Cookies": cookie},
        ) as session:
            async with session.get(
                url=URL.home_page,
                timeout=REQUEST_TIMEOUT,
                ssl=SSL_STATUS,
            ) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")

        if soup.find("input", attrs={"name": "Input.email"}) or soup.find(
            "input", attrs={"name": "Input.lastname"}
        ):
            raise AuthenticationError("Необходима авторизация")

        card_box = soup.find("div", class_="card-box")
        if not card_box:
            raise InvalidResponseError("Не найден блок .card-box")

        form_groups = card_box.find_all("div", class_="form-group")
        if not form_groups:
            raise InvalidResponseError("Не найдены .form-group")

        result: list[dict] = []
        for group in form_groups:
            label = group.find("label")
            value_div = group.find("div")
            if not label or not value_div:
                raise InvalidResponseError("Неполная пара label-value")

            result.append(
                {
                    "label": label.get_text(strip=True),
                    "value": value_div.get_text(strip=True),
                }
            )

        return result

    except (TimeoutError, ClientConnectorError) as err:
        raise SiteUnavailableError from err
