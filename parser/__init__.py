import os

import pytz
from dotenv import load_dotenv


class ParsingConfig:
    tz = pytz.timezone("Europe/Moscow")
    user_agent = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        )
    }


load_dotenv()
SSL_STATUS = os.getenv("SSL_STATUS", "true").lower() in {"1", "true", "yes", "on"}
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))


class URL:
    auth_url = {
        "nbook": "https://studstat.dgu.ru/Account/Login?ReturnUrl=%2F",
        "email": "https://studstat.dgu.ru/Account/Loginemail",
    }
    absence_page = "https://studstat.dgu.ru/Absence"
    progress_partial = "https://studstat.dgu.ru/Partial/Progress"
    absence_partial = "https://studstat.dgu.ru/Partial/Absence"
    timetable_api = {
        "GetTypeGroup": "https://raspisanie.dgu.ru/api/Content/GetTypeGroup",
        "GetTimeTables": "https://raspisanie.dgu.ru/api/Content/GetTimeTables",
    }
    ShowUserInformation_API = "https://studstat.dgu.ru/Modals/ShowUserInformation"
    home_page = "https://studstat.dgu.ru/"
    progress_url = "https://studstat.dgu.ru/Progress"
    timetables_page = "http://iit.dgu.ru/student/timetable"


__all__ = [
    "SSL_STATUS",
    "REQUEST_TIMEOUT",
    "URL",
    "ParsingConfig",
]
