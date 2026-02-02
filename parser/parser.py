"""
DEPRECATED: старый парсер. Оставлен как архив, не используется в проекте.
"""

from bs4 import BeautifulSoup
from contextlib import suppress
import aiohttp
import pytz
import re

from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError

from modules.database import db

import config
from tg_logger import TelegramLogger
from utils import get_now_datetime


class InvalidDataError(Exception):
    pass


class NoGradesFoundError(Exception):
    pass


class URL:
    auth_url = {
        'nbook': 'https://studstat.dgu.ru/Account/Login?ReturnUrl=%2F',
        'email': 'https://studstat.dgu.ru/Account/Loginemail'
    }
    timetable_api = {
        'GetTypeGroup': 'https://raspisanie.dgu.ru/api/Content/GetTypeGroup',
        'GetTimeTables': 'https://raspisanie.dgu.ru/api/Content/GetTimeTables'
    }
    ShowUserInformation_API = 'https://studstat.dgu.ru/Modals/ShowUserInformation'
    home_page = 'https://studstat.dgu.ru/'
    progress_url = 'https://studstat.dgu.ru/Progress'
    timetables_page = 'http://iit.dgu.ru/student/timetable'


class ParsingConfig:
    tz = pytz.timezone('Europe/Moscow')

    user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/58.0.3029.110 Safari/537.3'}


async def make_request(url: str, cookie: str | None = None, params: dict | None = None,
                       response_type: str | None = None):
    """
    Функция отправки GET запроса с помощью aiohttp
    :param url: URL-адрес
    :param cookie: Cookie-данные студента с сайта studstat.dgu.ru
    :param params: Параметры URL-запроса
    :param response_type: Тип результата
    :return: Содержание результата запроса
    """
    if cookie:
        cookie = {'.AspNetCore.Cookies': cookie}
    try:
        async with aiohttp.ClientSession(
                headers=ParsingConfig.user_agent,
                cookies=cookie
        ) as session:
            async with session.get(
                    url=url,
                    params=params,
                    timeout=6,
                    ssl=config.ssl_status
            ) as response:
                if response_type == 'json':
                    return await response.json()
                return await response.text()

    except (TimeoutError, ClientConnectorError) as err:
        raise err
    except Exception as err:
        raise err


async def cookie_reload(logger: TelegramLogger) -> None:
    auth_data = 'Гасанов Ислам Маратович 29191'.split()
    nbook = '29191'

    cookie = await collecting_cookies('nbook', auth_data, nbook)

    db.set_module_value('cookies', cookie)

    await logger.debug(f'Куки обновлены - {cookie[:20]}', stack=True)


async def student_authentication(user_id: int, auth_type, auth_data: list) -> bool:
    """
    Функция для авторизации студента на сайте и идентификация его в боте
    :param user_id: tg-ID студента
    :param auth_type: Тип авторизации (nbook или email)
    :param auth_data: Данные для дальнейшей авторизации (фио, зачетка, почта, пароль)
    :return: Статус попытки авторизации
    """

    nbook = auth_data[3] if len(auth_data) > 3 else ''
    email = auth_data[0] if len(auth_data) == 2 else ''
    password = auth_data[1] if len(auth_data) == 2 else ''

    # Получаем cookie данные
    cookies = await collecting_cookies(auth_type, auth_data, nbook)

    if cookies:
        # Получаем student_id
        student_id = await get_stud_id(cookies)
        # Получаем курс и форму обучения студента
        course, education_kind = await get_student_course(cookies, student_id)
        # Получаем данные студента
        (lastname, firstname, middlename,
         filial, faculty, departament, departament_number, student_status) = await get_student_data(cookies)

        # Обновляем базы данных
        db.set_student_data(user_id, lastname, firstname, middlename, nbook, email, password,
                            filial, faculty, departament, departament_number, student_status,
                            course, education_kind)
        db.set_entry_value(user_id, 'studstat_data', 'student_id', student_id)
        db.student_auth_confirm(user_id)

    else:
        return False

    return True


async def collecting_cookies(auth_type: str, auth_data: list, nbook: str | None = None) -> str:
    async with aiohttp.ClientSession(headers=ParsingConfig.user_agent) as session:
        async with session.get(
                url=URL.auth_url[auth_type],
                timeout=6,
                ssl=config.ssl_status
        ) as login_page:

            login_page_content = await login_page.text()

            soup = BeautifulSoup(login_page_content, "html.parser")
            auth_token = soup.find('input', attrs={'name': '__RequestVerificationToken'})['value']

            if auth_type == 'nbook':
                data = {
                    "Input.lastname": auth_data[0].capitalize(),
                    "Input.firstname": auth_data[1].capitalize(),
                    "Input.patr": auth_data[2].capitalize(),
                    "Input.nbook": nbook,
                    "__RequestVerificationToken": auth_token
                }
            elif auth_type == 'email':
                data = {
                    "Input.email": auth_data[0].capitalize(),
                    "Input.password": auth_data[1].capitalize(),
                    "__RequestVerificationToken": auth_token
                }

            # Отправляем POST запрос для авторизации
            await session.post(url=URL.auth_url[auth_type], data=data, ssl=config.ssl_status)

            # Ищем нужные cookie данные
            # noinspection PyTypeChecker
            cookies = session.cookie_jar.filter_cookies(request_url="https://studstat.dgu.ru")

            cookie_value = None
            for key, cookie in cookies.items():
                if cookie.key == ".AspNetCore.Cookies":
                    cookie_value = cookie.value

            if cookie_value is None:
                raise InvalidDataError

    return cookie_value


async def get_timetable_files():
    """
    Функция для получения ссылок на PDF-файлы расписания 1 и 2 недель с сайта "http://iit.dgu.ru/"
    :return: timetable_1_week - расписание 1 недели(URL), timetable_2_week - расписание 2 недели(URL)
    """

    iit_dgu_page = await make_request(url=URL.timetables_page)
    soup = BeautifulSoup(iit_dgu_page, 'html.parser')

    timetables = soup.find('div', class_='timetable__block-bachelor height')
    timetables_links = timetables.find_all('a', class_='timetable__link')
    timetable_1_week = timetables_links[0]['href']
    timetable_2_week = timetables_links[1]['href']

    return timetable_1_week, timetable_2_week


async def get_student_data(cookie: str):
    """
    Функция получения персональных данных студента
    :param cookie: Cookie-данные студента с сайта studstat.dgu.ru
    :return:
    """
    url = 'https://studstat.dgu.ru/'

    response = await make_request(url=url, cookie=cookie)
    student_data = response

    soup = BeautifulSoup(student_data, 'html.parser')

    card_box = soup.find("div", class_='card-box')
    student_card_l = card_box.find_all("div", class_='col-xs-6 text-left')

    lastname = student_card_l[0].text.strip().split(" ")[0].capitalize()
    firstname = student_card_l[0].text.strip().split(" ")[1].capitalize()
    middlename = student_card_l[0].text.strip().split(" ")[2].capitalize()
    filial = student_card_l[1].text.strip()
    faculty = student_card_l[2].text.strip()
    departament = student_card_l[3].text.strip()
    departament_number = departament.split(" ")[0]
    student_status = student_card_l[4].text.strip()

    return lastname, firstname, middlename, filial, faculty, departament, departament_number, student_status


async def get_stud_id(stud_cookies: str) -> str:
    """
    Функция для получения stud_id студента (http://studstat.dgu.ru/)
    :param stud_cookies: Cookie-данные студента с сайта studstat.dgu.ru
    :return: stud_id - Идентификатор студента на сайте studstat.dgu.ru
    """
    url = 'https://studstat.dgu.ru/Progress'

    response = await make_request(url=url, cookie=stud_cookies)
    soup = BeautifulSoup(response, 'html.parser')

    script = soup.find_all('script', type='text/javascript')[3]

    match = re.search(r'var stud_id = (\d+);', script.string)
    stud_id = match.group(1)

    return stud_id


async def get_student_course(stud_cookies: str, student_id: str):
    url = f'{URL.ShowUserInformation_API}?id={student_id}'

    response = await make_request(url, cookie=stud_cookies)
    soup = BeautifulSoup(response, 'html.parser')

    data_table = soup.find_all("table", class_="table jumbotron")[1]
    box = data_table.find_all("tr")[3].find_all("td")
    eduKind = box[1].text
    course = box[3].text.split(" ")[0]

    return course, eduKind


async def grades_parsing(grades_data, result_msg: str | None = ''):
    unavaliable_data = '👀 Пусто! Данных еще нет...\n\n'
    empty = ['', ' ', ' ']
    soup = BeautifulSoup(grades_data, 'html.parser')
    all_data = soup.find('tbody')
    tr_subjects_data = all_data.find_all('tr')

    for tr_subject_data in tr_subjects_data:
        td_subjects_data = tr_subject_data.find_all('td')
        result = []

        for td_subject_data in td_subjects_data:
            result.append(td_subject_data.text)

        exam_data = 2
        # subject_msg = f"<b><u>{result[0]}</u></b>\n"
        subject_msg = f"<blockquote><b>{result[0]}</b></blockquote>\n"

        # (!) Если данных за семестр еще нет
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

        result_msg += f'{subject_msg}\n'

    return result_msg


async def get_student_grades(user_id):
    """
    Функция парсинга успеваемости студента
    :param user_id: tg-ID студента
    :return: Сообщение содержания всех отметок студента за выбранный семестр
    """

    selected_semester = db.get_student_setting(user_id, 'selected_semester')
    stud_id = db.get_entry_value(user_id, 'studstat_data', 'student_id')
    stud_cookies = db.get_module_value('cookies')

    url = 'https://studstat.dgu.ru/Partial/Progress'

    params = {
        'stud_id': str(stud_id),
        'sess_id': str(selected_semester)
    }

    now_datetime = await get_now_datetime('%d.%m.20%y %H:%M')
    title_msg = (f'<blockquote><b>🎓 Ваша успеваемость за {str(selected_semester)} семестр!</b>\n'
                 f'<i>Обновлено: {now_datetime}</i></blockquote>\n\n')
    end_msg = 'Выберите интересующий вас семестр:'

    grades_data = await make_request(url=url, cookie=stud_cookies, params=params)
    result_msg = await grades_parsing(grades_data)

    GRADES_MSG = title_msg + result_msg + end_msg

    return GRADES_MSG


async def get_student_grades_mailing(user_id: int, selected_semester: str):
    """
    Функция парсинга успеваемости студента
    :param selected_semester: Выбранный семестр
    :param user_id: tg-ID студента
    :return: Сообщение содержания всех отметок студента за выбранный семестр
    """
    stud_id = db.get_entry_value(user_id, 'studstat_data', 'student_id')
    stud_cookies = db.get_module_value('cookies')

    url = 'https://studstat.dgu.ru/Partial/Progress'

    params = {
        'stud_id': str(stud_id),
        'sess_id': str(selected_semester)
    }

    grades_data = await make_request(url=url, cookie=stud_cookies, params=params)
    result_msg = await grades_parsing(grades_data)
    if '👀 Пусто! Данных еще нет...' in result_msg:
        raise NoGradesFoundError

    return result_msg


async def absences_parsing(absences_data, result_msg: str | None = ''):
    unavaliable_data = '👀 Пусто! Данных еще нет...\n'

    soup = BeautifulSoup(absences_data, 'html.parser')

    good_reason_absences = soup.find('tfoot')
    tr_good_reason_absences = good_reason_absences.find('tr')
    td_good_reason_absences = tr_good_reason_absences.find_all('th')

    num_emo = {'1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣'}

    # ========== ПРОПУСКИ ПО УВ. ПРИЧИНЕ ===========
    for_good_reason = []
    for good_reason_pass in td_good_reason_absences:
        for_good_reason.append(good_reason_pass.text)

    total_good_reason_absences = len(for_good_reason) - 1

    for_good_reason_msg = f"<blockquote>😇 <b>{for_good_reason[0]}</b></blockquote>"

    count_modules = 1
    for_good_reason_modules = for_good_reason[1:-1]
    for module_absences in for_good_reason_modules:
        for_good_reason_msg += f'\n{num_emo[str(count_modules)]} Модуль: <code>{module_absences}</code>'
        count_modules += 1

    # добавляем скок было пропусков по ув причине итого по индексу total_good_reason_absences
    for_good_reason_msg += (f'\n🚪<b>Итого по ув. причине:</b> '
                            f'<code>{for_good_reason[total_good_reason_absences]}</code>\n')
    # ========== ПРОПУСКИ ПО УВ. ПРИЧИНЕ ===========

    all_subjects_absences = soup.find('tbody')
    tr_absences = all_subjects_absences.find_all('tr')

    # 3 - при 1м модуле
    # 4 - при 2х модулях
    # 5 - при 3х модулях
    # 6 - при 4х модулях

    for tr_absence in tr_absences:
        td_absences = tr_absence.find_all('td')
        result = []
        for td_absence in td_absences:
            result.append(td_absence.text)

        subject_msg = f"<blockquote><b>{result[0]}</b></blockquote>\n"

        # (!) Если данных за семестр еще нет
        if "Нет данных!" in subject_msg:
            return unavaliable_data

        if result[1] != ' ':
            subject_msg += f"1️⃣ Модуль: <code>{result[1]}</code>\n"
        if result[2] != ' ' and len(td_absences) > 3:
            subject_msg += f"2️⃣ Модуль: <code>{result[2]}</code>\n"
        if len(result) > 3:
            if result[3] != ' ' and len(td_absences) > 4:
                subject_msg += f"3️⃣ Модуль: <code>{result[3]}</code>\n"
        if len(result) > 4:
            if result[4] != ' ' and len(td_absences) > 5:
                subject_msg += f"4️⃣ Модуль: <code>{result[4]}</code>\n"
        if len(result) > 5:
            if result[5] != ' ' and len(td_absences) > 6:
                subject_msg += f"4️⃣ Модуль: <code>{result[5]}</code>\n"

        subject_msg += f"🚶‍♂️ <b>Всего:</b> <code>{result[-1]}</code>\n\n"

        result_msg += subject_msg

    result_msg += for_good_reason_msg

    return result_msg


async def get_student_absences(user_id):
    """
    Функция парсинга пропусков студента
    :param user_id: tg-ID студента
    :return: Сообщение содержания всех пропусков студента за выбранный семестр
    """
    selected_semester = db.get_student_setting(user_id, 'selected_semester')
    stud_id = db.get_entry_value(user_id, 'studstat_data', 'student_id')
    stud_cookies = db.get_module_value('cookies')

    url = 'https://studstat.dgu.ru/Partial/Absence'

    params = {
        'stud_id': str(stud_id),
        'sess_id': str(selected_semester)
    }

    now_datetime = await get_now_datetime('%d.%m.20%y %H:%M')
    title_msg = (f'<blockquote><b>🚪 Ваши пропуски за {str(selected_semester)} семестр!</b>\n'
                 f'<i>Обновлено: {now_datetime}</i></blockquote>\n\n')
    end_msg = '\nВыберите интересующий вас семестр:'

    absences_data = await make_request(url=url, cookie=stud_cookies, params=params)
    result_msg = await absences_parsing(absences_data)

    ABSENCES_MSG = title_msg + result_msg + end_msg

    return ABSENCES_MSG


async def timetable_GetTypeGroup(data) -> dict:
    params = {
        'filId': data[0],
        'facId': data[1],
        'department': data[6],
        'course': data[4],
        'edukindId': data[2],
        'eduDegreeId': data[3],
        'typeWeekId': '1',
    }

    return await make_request(URL.timetable_api["GetTypeGroup"], params=params, response_type='json')


async def timetable_GetTimeTables(data: list, typeWeekId: str) -> dict:
    if data[5] == '99':
        params = {
            'filId': data[0],
            'facId': data[1],
            'edukindId': data[2],
            'eduDegreeId': data[3],
            'course': data[4],
            'typeWeekId': typeWeekId,
            'department': data[6]
        }
    else:
        params = {
            'filId': data[0],
            'facId': data[1],
            'edukindId': data[2],
            'eduDegreeId': data[3],
            'course': data[4],
            'typeGroupId': data[5],
            'typeWeekId': typeWeekId,
            'department': data[6]
        }

    return await make_request(URL.timetable_api["GetTimeTables"], params=params, response_type='json')
