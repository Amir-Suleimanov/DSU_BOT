from bs4 import BeautifulSoup

from . import URL
from .core import make_request


async def get_timetable_files():
    """
    Получить ссылки на PDF-файлы расписания 1 и 2 недель.
    """
    iit_dgu_page = await make_request(url=URL.timetables_page)
    soup = BeautifulSoup(iit_dgu_page, "html.parser")

    timetables = soup.find("div", class_="timetable__block-bachelor height")
    timetables_links = timetables.find_all("a", class_="timetable__link")
    timetable_1_week = timetables_links[0]["href"]
    timetable_2_week = timetables_links[1]["href"]

    return timetable_1_week, timetable_2_week


async def timetable_GetTypeGroup(data) -> dict:
    params = {
        "filId": data[0],
        "facId": data[1],
        "department": data[6],
        "course": data[4],
        "edukindId": data[2],
        "eduDegreeId": data[3],
        "typeWeekId": "1",
    }

    return await make_request(
        URL.timetable_api["GetTypeGroup"],
        params=params,
        response_type="json",
    )


async def timetable_GetTimeTables(data: list, typeWeekId: str) -> dict:
    if data[5] == "99":
        params = {
            "filId": data[0],
            "facId": data[1],
            "edukindId": data[2],
            "eduDegreeId": data[3],
            "course": data[4],
            "typeWeekId": typeWeekId,
            "department": data[6],
        }
    else:
        params = {
            "filId": data[0],
            "facId": data[1],
            "edukindId": data[2],
            "eduDegreeId": data[3],
            "course": data[4],
            "typeGroupId": data[5],
            "typeWeekId": typeWeekId,
            "department": data[6],
        }

    return await make_request(
        URL.timetable_api["GetTimeTables"],
        params=params,
        response_type="json",
    )
