from bs4 import BeautifulSoup

from . import URL, ParsingConfig
from .core import make_request
from datetime import datetime


def _now_datetime(fmt: str) -> str:
    return datetime.now(tz=ParsingConfig.tz).strftime(fmt)


async def absences_parsing(absences_data, result_msg: str | None = ""):
    unavaliable_data = "👀 Пусто! Данных еще нет...\n"

    soup = BeautifulSoup(absences_data, "html.parser")

    good_reason_absences = soup.find("tfoot")
    tr_good_reason_absences = good_reason_absences.find("tr")
    td_good_reason_absences = tr_good_reason_absences.find_all("th")

    num_emo = {"1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣"}

    for_good_reason = []
    for good_reason_pass in td_good_reason_absences:
        for_good_reason.append(good_reason_pass.text)

    total_good_reason_absences = len(for_good_reason) - 1

    for_good_reason_msg = f"<blockquote>😇 <b>{for_good_reason[0]}</b></blockquote>"

    count_modules = 1
    for_good_reason_modules = for_good_reason[1:-1]
    for module_absences in for_good_reason_modules:
        for_good_reason_msg += (
            f"\n{num_emo[str(count_modules)]} Модуль: <code>{module_absences}</code>"
        )
        count_modules += 1

    for_good_reason_msg += (
        f"\n🚪<b>Итого по ув. причине:</b> "
        f"<code>{for_good_reason[total_good_reason_absences]}</code>\n"
    )

    all_subjects_absences = soup.find("tbody")
    tr_absences = all_subjects_absences.find_all("tr")

    for tr_absence in tr_absences:
        td_absences = tr_absence.find_all("td")
        result = []
        for td_absence in td_absences:
            result.append(td_absence.text)

        subject_msg = f"<blockquote><b>{result[0]}</b></blockquote>\n"

        if "Нет данных!" in subject_msg:
            return unavaliable_data

        if result[1] != " ":
            subject_msg += f"1️⃣ Модуль: <code>{result[1]}</code>\n"
        if result[2] != " " and len(td_absences) > 3:
            subject_msg += f"2️⃣ Модуль: <code>{result[2]}</code>\n"
        if len(result) > 3:
            if result[3] != " " and len(td_absences) > 4:
                subject_msg += f"3️⃣ Модуль: <code>{result[3]}</code>\n"
        if len(result) > 4:
            if result[4] != " " and len(td_absences) > 5:
                subject_msg += f"4️⃣ Модуль: <code>{result[4]}</code>\n"
        if len(result) > 5:
            if result[5] != " " and len(td_absences) > 6:
                subject_msg += f"4️⃣ Модуль: <code>{result[5]}</code>\n"

        subject_msg += f"🚶‍♂️ <b>Всего:</b> <code>{result[-1]}</code>\n\n"

        result_msg += subject_msg

    result_msg += for_good_reason_msg

    return result_msg


async def get_student_absences(
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
        f"<blockquote><b>🚪 Ваши пропуски за {str(selected_semester)} семестр!</b>\n"
        f"<i>Обновлено: {now_datetime}</i></blockquote>\n\n"
    )
    end_msg = "\nВыберите интересующий вас семестр:"

    absences_data = await make_request(
        url=URL.absence_partial, cookie=stud_cookies, params=params
    )
    result_msg = await absences_parsing(absences_data)

    return title_msg + result_msg + end_msg
