import aiohttp
from bs4 import BeautifulSoup
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError

from . import URL, ParsingConfig, SSL_STATUS, REQUEST_TIMEOUT
from .exeptions import SiteUnavailableError, AuthenticationError, InvalidResponseError


async def get_student_information_page(cookie: str, student_id: str) -> str:
    try:
        async with aiohttp.ClientSession(
            headers=ParsingConfig.user_agent,
            cookies={".AspNetCore.Cookies": cookie},
        ) as session:
            async with session.get(
                url=URL.ShowUserInformation_API,
                params={"id": student_id},
                timeout=REQUEST_TIMEOUT,
                ssl=SSL_STATUS,
            ) as response:
                return await response.text()
    except (TimeoutError, ClientConnectorError) as err:
        raise SiteUnavailableError from err


def parse_student_information(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    if soup.find("input", attrs={"name": "Input.email"}) or soup.find(
        "input", attrs={"name": "Input.lastname"}
    ):
        raise AuthenticationError("Необходима авторизация")

    panel = soup.select_one(".panel-body")
    if not panel:
        raise InvalidResponseError("Не найден блок .panel-body")

    tables = panel.select("table.jumbotron")
    if len(tables) < 2:
        raise InvalidResponseError("Ожидалось минимум 2 таблицы .jumbotron")

    fio_cell = tables[0].select_one("td.divInfo")
    if not fio_cell:
        raise InvalidResponseError("Не найдено поле ФИО (td.divInfo)")

    rows = tables[1].select("tr")
    if len(rows) < 4:
        raise InvalidResponseError("Недостаточно строк в таблице 'Место учебы'")

    branch_cell = rows[0].select_one("td.divInfo")
    faculty_cell = rows[1].select_one("td.divInfo")
    specialty_cell = rows[2].select_one("td.divInfo")
    last_row_cells = rows[3].select("td.divInfo")

    if not branch_cell or not faculty_cell or not specialty_cell:
        raise InvalidResponseError("Не найдены обязательные поля в таблице 'Место учебы'")
    if len(last_row_cells) < 2:
        raise InvalidResponseError(
            "Не найдены поля 'Форма обучения' и 'Курс' в последней строке"
        )

    action_type_input = panel.select_one("#ActionType")
    action_type = action_type_input.get("value", "").strip() if action_type_input else ""

    return {
        "fio": fio_cell.get_text(strip=True),
        "branch": branch_cell.get_text(strip=True),
        "faculty": faculty_cell.get_text(strip=True),
        "specialty": specialty_cell.get_text(strip=True),
        "study_form": last_row_cells[0].get_text(strip=True),
        "course": last_row_cells[1].get_text(strip=True),
        "action_type": action_type,
    }


async def get_student_information_data(cookie: str, student_id: str) -> dict:
    html = await get_student_information_page(cookie, student_id)
    return parse_student_information(html)
