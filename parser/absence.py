import aiohttp
from bs4 import BeautifulSoup
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError
import re

from . import URL, ParsingConfig, SSL_STATUS, REQUEST_TIMEOUT
from .exeptions import SiteUnavailableError, AuthenticationError, InvalidResponseError


async def get_absence_page(cookie: str) -> str:
    try:
        async with aiohttp.ClientSession(
            headers=ParsingConfig.user_agent,
            cookies={".AspNetCore.Cookies": cookie},
        ) as session:
            async with session.get(
                url=URL.absence_page,
                timeout=REQUEST_TIMEOUT,
                ssl=SSL_STATUS,
            ) as response:
                return await response.text()
    except (TimeoutError, ClientConnectorError) as err:
        raise SiteUnavailableError from err


def parse_stud_id(html: str) -> str:
    match = re.search(r"var stud_id\s*=\s*(\d+);", html)
    if not match:
        raise InvalidResponseError("Не удалось извлечь stud_id из страницы Absence")
    return match.group(1)


def _validate_semester(semester: str | int) -> str:
    value = str(semester).strip()
    if not value.isdigit():
        raise InvalidResponseError("Некорректный semester: ожидается числовое значение")
    return value


async def get_absence_partial_page(cookie: str, stud_id: str, semester: str | int) -> str:
    sess_id = _validate_semester(semester)
    last_error: Exception | None = None
    for _ in range(3):
        try:
            async with aiohttp.ClientSession(
                headers=ParsingConfig.user_agent,
                cookies={".AspNetCore.Cookies": cookie},
            ) as session:
                async with session.get(
                    url=URL.absence_partial,
                    params={"stud_id": str(stud_id), "sess_id": sess_id},
                    headers={
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": URL.absence_page,
                    },
                    timeout=REQUEST_TIMEOUT,
                    ssl=SSL_STATUS,
                ) as response:
                    return await response.text()
        except (TimeoutError, ClientConnectorError) as err:
            last_error = err
            continue
    raise SiteUnavailableError from last_error


def parse_absence_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    if soup.find("input", attrs={"name": "Input.email"}) or soup.find(
        "input", attrs={"name": "Input.lastname"}
    ):
        raise AuthenticationError("Необходима авторизация")

    rows = soup.select("#absenceDiv tbody tr")
    if not rows:
        rows = soup.select("tbody tr")
    subjects: list[dict] = []

    for row in rows:
        cells = row.select("td")
        if len(cells) < 2:
            raise InvalidResponseError(
                "Неверная структура строки пропусков: ожидалось минимум 2 ячейки"
            )

        values = [cell.get_text(strip=True) for cell in cells]
        subjects.append(
            {
                "subject": values[0],
                "modules": values[1:-1],
                "total": values[-1],
            }
        )

    footer_row = soup.select_one("#absenceDiv tfoot tr")
    if not footer_row:
        footer_row = soup.select_one("tfoot tr")
    if not footer_row:
        return {
            "subjects": subjects,
            "footer": {
                "label": "",
                "modules": [],
                "total": "",
            },
        }

    footer_cells = footer_row.select("th")
    if len(footer_cells) < 2:
        raise InvalidResponseError(
            "Неверная структура итоговой строки пропусков: ожидалось минимум 2 ячейки"
        )

    footer_values = [cell.get_text(strip=True) for cell in footer_cells]
    footer = {
        "label": footer_values[0],
        "modules": footer_values[1:-1],
        "total": footer_values[-1],
    }

    return {
        "subjects": subjects,
        "footer": footer,
    }


async def get_absence_data(cookie: str) -> dict:
    html = await get_absence_page(cookie)
    return parse_absence_page(html)


async def get_absence_data_by_semester(
    cookie: str,
    semester: str | int,
    stud_id: str | None = None,
) -> dict:
    student_id = stud_id
    if not student_id:
        full_page_html = await get_absence_page(cookie)
        student_id = parse_stud_id(full_page_html)

    partial_html = await get_absence_partial_page(cookie, student_id, semester)
    result = parse_absence_page(partial_html)
    result["stud_id"] = str(student_id)
    result["semester"] = _validate_semester(semester)
    return result
