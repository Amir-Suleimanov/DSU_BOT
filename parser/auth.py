import aiohttp
from bs4 import BeautifulSoup
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError
from yarl import URL as YarlURL

from . import URL, ParsingConfig, SSL_STATUS, REQUEST_TIMEOUT
from .exeptions import SiteUnavailableError, AuthenticationError, InvalidResponseError
from .base import main_page
from .progress import get_progress_page, parse_progress_page, parse_stud_id
from .student_information import get_student_information_data
from database.models import Auth


class InvalidDataError(AuthenticationError):
    default_message = "Неверные данные для входа"


async def login_by_nbook(lastname: str, firstname: str, patr: str, nbook: str) -> str:
    """
    Возвращает значение cookie ".AspNetCore.Cookies" при успешном входе.
    """
    return await _authenticate(
        URL.auth_url["nbook"],
        {
            "Input.lastname": lastname,
            "Input.firstname": firstname,
            "Input.patr": patr,
            "Input.nbook": nbook,
        },
    )


async def login_by_email(email: str, password: str) -> str:
    """
    Возвращает значение cookie ".AspNetCore.Cookies" при успешном входе.
    """
    return await _authenticate(
        URL.auth_url["email"],
        {
            "Input.email": email,
            "Input.password": password,
        },
    )


async def _authenticate(url: str, payload: dict) -> str:
    try:
        async with aiohttp.ClientSession(headers=ParsingConfig.user_agent) as session:
            async with session.get(
                url=url,
                timeout=REQUEST_TIMEOUT,
                ssl=SSL_STATUS,
            ) as login_page:
                login_page_content = await login_page.text()

            soup = BeautifulSoup(login_page_content, "html.parser")
            token_input = soup.find(
                "input", attrs={"name": "__RequestVerificationToken"}
            )
            if not token_input:
                raise InvalidResponseError("Не найден __RequestVerificationToken")

            payload["__RequestVerificationToken"] = token_input["value"]

            post_response = await session.post(
                url=url,
                data=payload,
                ssl=SSL_STATUS,
                timeout=REQUEST_TIMEOUT,
            )

            post_html = await post_response.text()
            post_soup = BeautifulSoup(post_html, "html.parser")
            validation_box = post_soup.find("div", class_="validation-summary-errors")
            if validation_box:
                error_li = validation_box.find("li")
                if error_li and error_li.text.strip():
                    raise AuthenticationError(error_li.text.strip())
                raise AuthenticationError("Неверные данные для входа")

            cookies = session.cookie_jar.filter_cookies(
                request_url=YarlURL("https://studstat.dgu.ru")
            )

            for _, cookie in cookies.items():
                if cookie.key == ".AspNetCore.Cookies":
                    return cookie.value

            raise AuthenticationError("Cookie авторизации не получена")

    except (TimeoutError, ClientConnectorError) as err:
        raise SiteUnavailableError from err


def _auth_type_key(auth_type: int) -> str:
    if auth_type == Auth.GBook():
        return "nbook"
    if auth_type == Auth.Email():
        return "email"
    raise InvalidDataError("Неизвестный тип авторизации")


def _split_fio(fio: str) -> tuple[str, str, str]:
    parts = fio.split()
    if len(parts) < 3:
        raise InvalidResponseError("Некорректное поле ФИО")
    return parts[1], parts[0], parts[2]


def _extract_status(main_data: list[dict]) -> str:
    for item in main_data:
        label = item.get("label", "").lower()
        if "статус" in label:
            return item.get("value", "")
    return ""


async def _build_profile_data(cookie: str, fallback_gradebook: str | None = None) -> dict:
    progress_html = await get_progress_page(cookie)
    stud_id = parse_stud_id(progress_html)
    progress_data = parse_progress_page(progress_html)
    student_info = await get_student_information_data(cookie, stud_id)
    main_data = await main_page(cookie)

    name, surname, patronymic = _split_fio(student_info["fio"])
    status = _extract_status(main_data)

    current_semester_raw = progress_data.get("current_semester", "")
    current_semester = int(current_semester_raw) if str(current_semester_raw).isdigit() else 1

    gradebook_number: int | None = None
    if fallback_gradebook and str(fallback_gradebook).isdigit():
        gradebook_number = int(fallback_gradebook)

    return {
        "stud_id": int(stud_id),
        "name": name,
        "surname": surname,
        "patronymic": patronymic,
        "gradebook_number": gradebook_number,
        "branch": student_info["branch"],
        "faculty": student_info["faculty"],
        "study_program": student_info["specialty"],
        "status": status,
        "current_semester": current_semester,
    }


async def student_authentication(
    auth_type: int,
    auth_data: list,
    is_student_data: bool = False,
):
    try:
        _auth_type_key(auth_type)
        if auth_type == Auth.GBook():
            if len(auth_data) != 4:
                raise InvalidDataError("Для входа по зачётке нужно 4 параметра")
            cookie = await login_by_nbook(
                lastname=auth_data[0],
                firstname=auth_data[1],
                patr=auth_data[2],
                nbook=auth_data[3],
            )
            if not is_student_data:
                return True
            return await _build_profile_data(cookie, fallback_gradebook=auth_data[3])

        if auth_type == Auth.Email():
            if len(auth_data) != 2:
                raise InvalidDataError("Для входа по email нужно 2 параметра")
            cookie = await login_by_email(email=auth_data[0], password=auth_data[1])
            if not is_student_data:
                return True
            return await _build_profile_data(cookie)

        raise InvalidDataError("Неизвестный тип авторизации")
    except AuthenticationError as err:
        raise InvalidDataError(str(err)) from err
