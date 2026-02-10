# Внешний API парсера (DSU_NEW/parser)

Короткое и целевое описание того, что нужно использовать извне парсера. Здесь перечислены публичные функции, их сигнатуры, ожидаемые параметры, возвращаемые значения и возможные исключения.

Используйте эти функции в своём коде — всё остальное внутри модуля является внутренней реализацией.

---

## Коротко — что использовать извне

Ниже перечислены только публичные функции, которые предназначены для вызова из кода вне пакета `parser`.

- Аутентификация
  - `login_by_email(email: str, password: str) -> str`
    - Возвращает: `cookie: str` (".AspNetCore.Cookies").
    - Исключения: `AuthenticationError`, `SiteUnavailableError`, `InvalidResponseError`.

  - `login_by_nbook(lastname: str, firstname: str, patr: str, nbook: str) -> str`
    - То же, но по данным зачётной книжки.

  - `student_authentication(auth_type: int, auth_data: list, is_student_data: bool = False)`
    - Удобная обёртка: при `is_student_data=False` возвращает `True` при успехе; при `True` возвращает `dict` с профилем студента.
    - Вход: `auth_type` — значение из `database.models.Auth`, `auth_data` — список полей (см. `parser/test_parser.py`).

- Общие данные (главная страница)
  - `main_page(cookie: str) -> list[dict]`
    - Возвращает: список пар `{label, value}`.

- Успеваемость
  - `get_progress_data(cookie: str) -> dict`
    - Возвращает: парсенный результат полной страницы успеваемости.
  - `get_progress_data_by_semester(cookie: str, semester: str|int, stud_id: str|None = None) -> dict`
    - Возвращает: то же, но для указанного семестра; добавляет `stud_id` и `semester`.

- Пропуски
  - `get_absence_data(cookie: str) -> dict`
    - Возвращает: парсенный результат полной страницы пропусков.
  - `get_absence_data_by_semester(cookie: str, semester: str|int, stud_id: str|None = None) -> dict`
    - Аналогично — для семестра; добавляет `stud_id` и `semester`.

- Информация о студенте
  - `get_student_information_data(cookie: str, student_id: str) -> dict`
    - Возвращает: `dict` с ключами `fio`, `branch`, `faculty`, `specialty`, `study_form`, `course`, `action_type`.

## Формат входных данных и общие замечания

- `cookie` — всегда строка: значение куки авторизации ".AspNetCore.Cookies".
- `semester` — число или строка, содержащая число (например, `5` или `"5"`).
- Все сетевые функции могут выбросить `SiteUnavailableError` при проблемах сети/таймаутах.
- При обнаружении, что нужна авторизация, парсер бросает `AuthenticationError`.
- При неожиданной структуре HTML — `InvalidResponseError`.

Если нужно, могу добавить короткие JSON-примеры возвращаемых структур для каждой из перечисленных функций.
