import aiohttp
from bs4 import BeautifulSoup
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError
import re

from . import URL, ParsingConfig, SSL_STATUS, REQUEST_TIMEOUT
from .exeptions import SiteUnavailableError, AuthenticationError, InvalidResponseError


async def get_progress_page(cookie: str) -> str:
    try:
        async with aiohttp.ClientSession(
            headers=ParsingConfig.user_agent,
            cookies={".AspNetCore.Cookies": cookie},
        ) as session:
            async with session.get(
                url=URL.progress_url,
                timeout=REQUEST_TIMEOUT,
                ssl=SSL_STATUS,
            ) as response:
                return await response.text()
    except (TimeoutError, ClientConnectorError) as err:
        raise SiteUnavailableError from err


def parse_stud_id(html: str) -> str:
    match = re.search(r"var stud_id\s*=\s*(\d+);", html)
    if not match:
        raise InvalidResponseError("Не удалось извлечь stud_id из страницы Progress")
    return match.group(1)


def _validate_semester(semester: str | int) -> str:
    value = str(semester).strip()
    if not value.isdigit():
        raise InvalidResponseError("Некорректный semester: ожидается числовое значение")
    return value


async def get_progress_partial_page(cookie: str, stud_id: str, semester: str | int) -> str:
    sess_id = _validate_semester(semester)
    try:
        async with aiohttp.ClientSession(
            headers=ParsingConfig.user_agent,
            cookies={".AspNetCore.Cookies": cookie},
        ) as session:
            async with session.get(
                url=URL.progress_partial,
                params={"stud_id": str(stud_id), "sess_id": sess_id},
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": URL.progress_url,
                },
                timeout=REQUEST_TIMEOUT,
                ssl=SSL_STATUS,
            ) as response:
                return await response.text()
    except (TimeoutError, ClientConnectorError) as err:
        raise SiteUnavailableError from err


def parse_progress_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    if soup.find("input", attrs={"name": "Input.email"}) or soup.find(
        "input", attrs={"name": "Input.lastname"}
    ):
        raise AuthenticationError("Необходима авторизация")

    current_semester_option = soup.select_one("#sess_id option[selected]")
    current_semester = ""
    semesters: list[dict] = []
    if current_semester_option:
        current_semester = current_semester_option.get("value", "").strip()
        if not current_semester:
            raise InvalidResponseError("У текущего семестра отсутствует value")

        semester_options = soup.select("#sess_id option")
        if not semester_options:
            raise InvalidResponseError("Не найдены опции семестров (#sess_id option)")

        for option in semester_options:
            value = option.get("value", "").strip()
            if not value:
                raise InvalidResponseError("Обнаружена опция семестра без value")
            semesters.append(
                {
                    "value": value,
                    "title": option.get_text(strip=True),
                    "selected": option.has_attr("selected"),
                }
            )

    rows = soup.select("#progressDiv tbody tr")
    if not rows:
        rows = soup.select("tbody tr")
    if not rows:
        return {
            "current_semester": current_semester,
            "semesters": semesters,
            "subjects": [],
        }

    subjects: list[dict] = []
    for row in rows:
        cells = row.select("td")
        if len(cells) < 4:
            raise InvalidResponseError(
                "Неверная структура строки успеваемости: ожидалось минимум 4 ячейки"
            )

        values = [cell.get_text(strip=True) for cell in cells]
        subjects.append(
            {
                "subject": values[0],
                "modules": values[1:-3],
                "coursework": values[-3],
                "credit": values[-2],
                "exam": values[-1],
            }
        )

    return {
        "current_semester": current_semester,
        "semesters": semesters,
        "subjects": subjects,
    }


async def get_progress_data(cookie: str) -> dict:
    html = await get_progress_page(cookie)
    return parse_progress_page(html)


async def get_progress_data_by_semester(
    cookie: str,
    semester: str | int,
    stud_id: str | None = None,
) -> dict:
    student_id = stud_id
    if not student_id:
        full_page_html = await get_progress_page(cookie)
        student_id = parse_stud_id(full_page_html)

    partial_html = await get_progress_partial_page(cookie, student_id, semester)
    result = parse_progress_page(partial_html)
    result["stud_id"] = str(student_id)
    result["semester"] = _validate_semester(semester)
    return result
