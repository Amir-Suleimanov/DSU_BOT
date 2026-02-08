from bs4 import BeautifulSoup
import aiohttp
import logging
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError

from . import URL, ParsingConfig, SSL_STATUS, REQUEST_TIMEOUT, SiteUnavailableError
from database.models import Auth
from .user_data import build_profile_data, get_stud_id


class InvalidDataError(Exception):
    def __init__(self, message: str = "Неверные данные для входа"):
        super().__init__(message)


def _auth_type_key(auth_type: int) -> str:
    if auth_type == Auth.GBook():
        return "nbook"
    if auth_type == Auth.Email():
        return "email"
    raise InvalidDataError("Неизвестный тип авторизации")


async def student_authentication(
    auth_type: int,
    auth_data: list,
    is_student_data: bool = False,
):
    """
    Авторизация студента на сайте.
    :param auth_type: Тип авторизации (Auth.GBook() или Auth.Email())
    :param auth_data: Данные для дальнейшей авторизации (фио, зачетка, почта, пароль)
    :param is_student_data: Если True — вернуть данные профиля
    :return: bool или dict с данными профиля
    """

    nbook = auth_data[3] if len(auth_data) > 3 else ""
    # Получаем cookie данные
    cookies = await collecting_cookies(auth_type, auth_data, nbook)

    if not cookies:
        return False

    if is_student_data:
        student_id = await get_stud_id(cookies)
        return await build_profile_data(cookies, student_id)

    return True


async def collecting_cookies(
    auth_type: int,
    auth_data: list,
    nbook: str | None = None,
) -> str:
    try:
        auth_type_key = _auth_type_key(auth_type)
        async with aiohttp.ClientSession(headers=ParsingConfig.user_agent) as session:
            async with session.get(
                url=URL.auth_url[auth_type_key],
                timeout=REQUEST_TIMEOUT,
                ssl=SSL_STATUS,
            ) as login_page:

                login_page_content = await login_page.text()

                soup = BeautifulSoup(login_page_content, "html.parser")
                auth_token_input = soup.find(
                    "input", attrs={"name": "__RequestVerificationToken"}
                )
                if not auth_token_input:
                    raise InvalidDataError
                auth_token = auth_token_input["value"]

                if auth_type == Auth.GBook():
                    data = {
                        "Input.lastname": auth_data[0],
                        "Input.firstname": auth_data[1],
                        "Input.patr": auth_data[2],
                        "Input.nbook": nbook,
                        "__RequestVerificationToken": auth_token,
                    }
                elif auth_type == Auth.Email():
                    data = {
                        "Input.email": auth_data[0],
                        "Input.password": auth_data[1],
                        "__RequestVerificationToken": auth_token,
                    }
                else:
                    raise InvalidDataError("Неизвестный тип авторизации")

                # Отправляем POST запрос для авторизации
                post_response = await session.post(
                    url=URL.auth_url[auth_type_key],
                    data=data,
                    ssl=SSL_STATUS,
                    timeout=REQUEST_TIMEOUT,
                )

                post_html = await post_response.text()
                post_soup = BeautifulSoup(post_html, "html.parser")
                validation_box = post_soup.find("div", class_="validation-summary-errors")
                if validation_box:
                    error_li = validation_box.find("li")
                    if error_li and error_li.text.strip():
                        raise InvalidDataError(error_li.text.strip())

                # Ищем нужные cookie данные
                # noinspection PyTypeChecker
                cookies = session.cookie_jar.filter_cookies(
                    request_url="https://studstat.dgu.ru"
                )

                cookie_value = None
                for key, cookie in cookies.items():
                    if cookie.key == ".AspNetCore.Cookies":
                        cookie_value = cookie.value

                if cookie_value is None:
                    raise InvalidDataError()

    except (TimeoutError, ClientConnectorError) as err:
        raise SiteUnavailableError from err
    except InvalidDataError as err:
        raise

    return cookie_value
