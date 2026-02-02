from datetime import datetime
from contextlib import suppress

from bs4 import BeautifulSoup

from . import URL, ParsingConfig
from .core import make_request


class NoGradesFoundError(Exception):
    pass


def _now_datetime(fmt: str) -> str:
    return datetime.now(tz=ParsingConfig.tz).strftime(fmt)


async def grades_parsing(grades_data, result_msg: str | None = ""):
    unavaliable_data = "👀 Пусто! Данных еще нет...\n\n"
    empty = ["", " ", " "]
    soup = BeautifulSoup(grades_data, "html.parser")
    all_data = soup.find("tbody")
    tr_subjects_data = all_data.find_all("tr")

    for tr_subject_data in tr_subjects_data:
        td_subjects_data = tr_subject_data.find_all("td")
        result = []

        for td_subject_data in td_subjects_data:
            result.append(td_subject_data.text)

        subject_msg = f"<blockquote><b>{result[0]}</b></blockquote>\n"

        if "Нет данных!" in subject_msg:
            return unavaliable_data

        with suppress(IndexError):
            if result[1] not in empty:
                subject_msg += f"1️⃣ Модуль: <code>{result[1]}</code>\n"

        with suppress(IndexError):
            if len(td_subjects_data) > 5:
                if result[2] not in empty:
                    subject_msg += f"2️⃣ Модуль: <code>{result[2]}</code>\n"

        with suppress(IndexError):
            if len(td_subjects_data) > 6:
                if result[3] not in empty:
                    subject_msg += f"3️⃣ Модуль: <code>{result[3]}</code>\n"

        with suppress(IndexError):
            if len(td_subjects_data) > 7:
                if result[4] not in empty:
                    subject_msg += f"4️⃣ Модуль: <code>{result[4]}</code>\n"

        with suppress(IndexError):
            if len(td_subjects_data) > 8:
                if result[5] not in empty:
                    subject_msg += f"5️⃣ Модуль: <code>{result[5]}</code>\n"

        with suppress(IndexError):
            if result[-3] not in empty:
                subject_msg += f"📝 <b>Курсовая:</b> <code>{result[-3]}</code>\n"

        with suppress(IndexError):
            if result[-2] not in empty:
                subject_msg += f"❕ <b>Зачет:</b> <code>{result[-2]}</code>\n"

        with suppress(IndexError):
            if result[-1] not in empty:
                subject_msg += f"‼️ <b>Экзамен:</b> <code>{result[-1]}</code>\n"

        result_msg += f"{subject_msg}\n"

    return result_msg


async def get_student_grades(
    stud_id: str,
    selected_semester: str,
    stud_cookies: str,
):
    params = {
        "stud_id": str(stud_id),
        "sess_id": str(selected_semester),
    }

    now_datetime = _now_datetime("%d.%m.20%y %H:%M")
    title_msg = (
        f"<blockquote><b>🎓 Ваша успеваемость за {str(selected_semester)} семестр!</b>\n"
        f"<i>Обновлено: {now_datetime}</i></blockquote>\n\n"
    )
    end_msg = "Выберите интересующий вас семестр:"

    grades_data = await make_request(
        url=URL.progress_partial, cookie=stud_cookies, params=params
    )
    result_msg = await grades_parsing(grades_data)

    return title_msg + result_msg + end_msg


async def get_student_grades_mailing(
    stud_id: str,
    selected_semester: str,
    stud_cookies: str,
):
    params = {
        "stud_id": str(stud_id),
        "sess_id": str(selected_semester),
    }

    grades_data = await make_request(
        url=URL.progress_partial, cookie=stud_cookies, params=params
    )
    result_msg = await grades_parsing(grades_data)
    if "👀 Пусто! Данных еще нет..." in result_msg:
        raise NoGradesFoundError

    return result_msg
