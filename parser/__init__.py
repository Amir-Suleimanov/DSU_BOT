from .core import ParsingConfig, SSL_STATUS, REQUEST_TIMEOUT, SiteUnavailableError


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
    "SiteUnavailableError",
    "URL",
    "ParsingConfig",
]
