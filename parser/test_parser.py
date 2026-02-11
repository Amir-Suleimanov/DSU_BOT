"""Pytest интеграционные тесты для parser.

Запуск:
    pytest parser/test_parser.py -s

Перед запуском заполните STUDENT_* поля ниже.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.models import Auth
from parser.absence import (
    get_absence_data,
    get_absence_data_by_semester,
    get_absence_page,
    get_absence_partial_page,
    parse_absence_page,
    parse_stud_id as parse_absence_stud_id,
)
from parser.auth import (
    login_by_email,
    login_by_nbook,
    student_authentication,
)
from parser.base import main_page
from parser.progress import (
    get_progress_data,
    get_progress_data_by_semester,
    get_progress_page,
    get_progress_partial_page,
    parse_progress_page,
    parse_stud_id as parse_progress_stud_id,
)
from parser.student_information import (
    get_student_information_data,
    get_student_information_page,
    parse_student_information,
)


# ==============================
# ДАННЫЕ СТУДЕНТА ДЛЯ ТЕСТОВ
# ==============================
STUDENT_LASTNAME = ""
STUDENT_FIRSTNAME = ""
STUDENT_PATRONYMIC = ""
STUDENT_GRADEBOOK = ""

STUDENT_EMAIL = os.getenv("STUDENT_EMAIL")
STUDENT_PASSWORD = os.getenv("STUDENT_PASSWORD")

# Семестр для тестов partial-ручек (например: "1", "2", "3" ...)
TEST_SEMESTER = "5"

# Необязательно: если известно, можно указать заранее. Если пусто, извлечется автоматически.
STUDENT_ID = ""


def _has_gbook_creds() -> bool:
    return all(
        [
            STUDENT_LASTNAME.strip(),
            STUDENT_FIRSTNAME.strip(),
            STUDENT_PATRONYMIC.strip(),
            STUDENT_GRADEBOOK.strip(),
        ]
    )


def _has_email_creds() -> bool:
    return bool(STUDENT_EMAIL.strip() and STUDENT_PASSWORD.strip())


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="session")
def cookie() -> str:
    if _has_gbook_creds():
        value = _run(
            login_by_nbook(
                STUDENT_LASTNAME.strip(),
                STUDENT_FIRSTNAME.strip(),
                STUDENT_PATRONYMIC.strip(),
                STUDENT_GRADEBOOK.strip(),
            )
        )
        assert value
        return value

    if _has_email_creds():
        value = _run(login_by_email(STUDENT_EMAIL.strip(), STUDENT_PASSWORD.strip()))
        assert value
        return value

    pytest.skip(
        "Не заполнены данные авторизации. "
        "Укажите либо ФИО+зачетка, либо email+password в parser/test_parser.py"
    )


@pytest.fixture(scope="session")
def stud_id(cookie: str) -> str:
    if STUDENT_ID.strip():
        return STUDENT_ID.strip()

    progress_html = _run(get_progress_page(cookie))
    value = parse_progress_stud_id(progress_html)
    assert value.isdigit()
    return value


def test_auth_nbook():
    if not _has_gbook_creds():
        pytest.skip("Не заполнены STUDENT_LASTNAME/STUDENT_FIRSTNAME/STUDENT_PATRONYMIC/STUDENT_GRADEBOOK")

    cookie = _run(
        login_by_nbook(
            STUDENT_LASTNAME.strip(),
            STUDENT_FIRSTNAME.strip(),
            STUDENT_PATRONYMIC.strip(),
            STUDENT_GRADEBOOK.strip(),
        )
    )
    assert cookie

    profile = _run(
        student_authentication(
            auth_type=Auth.GBook(),
            auth_data=[
                STUDENT_LASTNAME.strip(),
                STUDENT_FIRSTNAME.strip(),
                STUDENT_PATRONYMIC.strip(),
                STUDENT_GRADEBOOK.strip(),
            ],
        )
    )
    assert isinstance(profile, dict)
    for key in [
        "stud_id",
        "name",
        "surname",
        "patronymic",
        "gradebook_number",
        "branch",
        "faculty",
        "study_program",
        "status",
        "current_semester",
    ]:
        assert key in profile


def test_auth_email():
    if not _has_email_creds():
        pytest.skip("Не заполнены STUDENT_EMAIL/STUDENT_PASSWORD")

    cookie = _run(login_by_email(STUDENT_EMAIL.strip(), STUDENT_PASSWORD.strip()))
    assert cookie

    profile = _run(
        student_authentication(
            auth_type=Auth.Email(),
            auth_data=[STUDENT_EMAIL.strip(), STUDENT_PASSWORD.strip()],
        )
    )
    assert isinstance(profile, dict)
    assert "stud_id" in profile
    assert "gradebook_number" in profile
    assert "current_semester" in profile


def test_base_main_page(cookie: str):
    data = _run(main_page(cookie))
    assert isinstance(data, list)
    if data:
        assert isinstance(data[0], dict)
        assert "label" in data[0]
        assert "value" in data[0]


def test_progress_full(cookie: str):
    html = _run(get_progress_page(cookie))
    assert isinstance(html, str) and html.strip()

    parsed = parse_progress_page(html)
    assert isinstance(parsed, dict)
    assert "subjects" in parsed

    full_data = _run(get_progress_data(cookie))
    assert isinstance(full_data, dict)
    assert "subjects" in full_data


def test_progress_partial(cookie: str, stud_id: str):
    partial_html = _run(get_progress_partial_page(cookie, stud_id, TEST_SEMESTER))
    assert isinstance(partial_html, str) and partial_html.strip()

    partial_parsed = parse_progress_page(partial_html)
    assert isinstance(partial_parsed, dict)
    assert "subjects" in partial_parsed

    by_sem = _run(get_progress_data_by_semester(cookie, TEST_SEMESTER, stud_id=stud_id))
    assert isinstance(by_sem, dict)
    assert by_sem.get("semester") == str(TEST_SEMESTER)
    assert by_sem.get("stud_id") == stud_id


def test_progress_parse_stud_id(cookie: str):
    html = _run(get_progress_page(cookie))
    value = parse_progress_stud_id(html)
    assert value.isdigit()


def test_absence_full(cookie: str):
    html = _run(get_absence_page(cookie))
    assert isinstance(html, str) and html.strip()

    parsed = parse_absence_page(html)
    assert isinstance(parsed, dict)
    assert "subjects" in parsed
    assert "footer" in parsed

    full_data = _run(get_absence_data(cookie))
    assert isinstance(full_data, dict)
    assert "footer" in full_data


def test_absence_partial(cookie: str, stud_id: str):
    partial_html = _run(get_absence_partial_page(cookie, stud_id, TEST_SEMESTER))
    assert isinstance(partial_html, str) and partial_html.strip()

    partial_parsed = parse_absence_page(partial_html)
    assert isinstance(partial_parsed, dict)
    assert "footer" in partial_parsed

    by_sem = _run(get_absence_data_by_semester(cookie, TEST_SEMESTER, stud_id=stud_id))
    assert isinstance(by_sem, dict)
    assert by_sem.get("semester") == str(TEST_SEMESTER)
    assert by_sem.get("stud_id") == stud_id


def test_absence_parse_stud_id(cookie: str):
    html = _run(get_absence_page(cookie))
    value = parse_absence_stud_id(html)
    assert value.isdigit()


def test_student_information(cookie: str, stud_id: str):
    html = _run(get_student_information_page(cookie, stud_id))
    assert isinstance(html, str) and html.strip()

    parsed = parse_student_information(html)
    assert isinstance(parsed, dict)
    for key in ["fio", "branch", "faculty", "specialty", "study_form", "course"]:
        assert key in parsed

    data = _run(get_student_information_data(cookie, stud_id))
    assert isinstance(data, dict)
    assert "fio" in data
