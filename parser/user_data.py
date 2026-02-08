from bs4 import BeautifulSoup
import re
from datetime import datetime

from . import URL, ParsingConfig
from .core import make_request


async def get_student_data(cookie: str):
    """
    Получение персональных данных студента.
    """
    response = await make_request(url=URL.home_page, cookie=cookie)
    soup = BeautifulSoup(response, "html.parser")

    card_box = soup.find("div", class_="card-box")
    student_card_l = card_box.find_all("div", class_="col-xs-6 text-left")

    lastname = student_card_l[0].text.strip().split(" ")[0].capitalize()
    firstname = student_card_l[0].text.strip().split(" ")[1].capitalize()
    middlename = student_card_l[0].text.strip().split(" ")[2].capitalize()
    filial = student_card_l[1].text.strip()
    faculty = student_card_l[2].text.strip()
    departament = student_card_l[3].text.strip()
    student_status = student_card_l[4].text.strip()

    return (
        lastname,
        firstname,
        middlename,
        filial,
        faculty,
        departament,
        student_status,
    )


async def get_stud_id(stud_cookies: str) -> str:
    """
    Получение stud_id студента.
    """
    response = await make_request(url=URL.progress_url, cookie=stud_cookies)
    soup = BeautifulSoup(response, "html.parser")

    script = soup.find_all("script", type="text/javascript")[3]
    match = re.search(r"var stud_id = (\d+);", script.string)
    return match.group(1)


async def get_student_course(stud_cookies: str, student_id: str):
    url = f"{URL.ShowUserInformation_API}?id={student_id}"

    response = await make_request(url, cookie=stud_cookies)
    soup = BeautifulSoup(response, "html.parser")

    data_table = soup.find_all("table", class_="table jumbotron")[1]
    box = data_table.find_all("tr")[3].find_all("td")
    edukind = box[1].text
    course = box[3].text.split(" ")[0]

    return course, edukind


async def build_profile_data(cookie: str, student_id: str) -> dict:
    """
    Сбор данных профиля для создания пользователя.
    """
    course, _ = await get_student_course(cookie, student_id)
    current_semester = await get_current_semester_from_absence(cookie)
    (
        lastname,
        firstname,
        middlename,
        filial,
        faculty,
        departament,
        student_status,
    ) = await get_student_data(cookie)

    if current_semester is None:
        current_semester = _current_semester_from_course(course)

    return {
        "name": firstname,
        "surname": lastname,
        "patronymic": middlename,
        "gradebook_number": student_id,
        "branch": filial,
        "faculty": faculty,
        "study_program": departament,
        "status": student_status,
        "current_semester": current_semester,
    }


def _current_semester_from_course(course: str) -> int:
    """
    На основе курса и времени года рассчитывает текущий семестр.
    Логика как в исходном парсере: источник курса тот же.
    """
    if not str(course).isdigit():
        return 1
    course_num = int(course)
    month = datetime.now(tz=ParsingConfig.tz).month
    if month >= 9:
        return course_num * 2 - 1
    return course_num * 2


async def get_current_semester_from_absence(cookie: str) -> int | None:
    """
    Пытается получить текущий семестр со страницы /Absence (select#sess_id).
    Возвращает None, если не удалось определить.
    """
    response = await make_request(url=URL.absence_page, cookie=cookie)
    soup = BeautifulSoup(response, "html.parser")

    select = soup.find("select", id="sess_id")
    if not select:
        return None

    selected = select.find("option", selected=True)
    if selected and selected.get("value"):
        value = selected.get("value")
        if str(value).isdigit():
            return int(value)

    options = select.find_all("option")
    if options:
        last_value = options[-1].get("value")
        if str(last_value).isdigit():
            return int(last_value)

    return None
