from typing import List, Optional
from datetime import time
from sqlalchemy import BigInteger, Integer, SmallInteger, Column, DateTime, String, Text, func, ForeignKey, Time
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class Auth(Base):
    user_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True, comment="Пользователь")
    method: Mapped[SmallInteger] = mapped_column(SmallInteger, nullable=False, comment="Метод аутентификации")    

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True, comment="Почта")
    password: Mapped[str] = mapped_column(String(255), nullable=True, comment="Хешированный пароль")

    __tablename__ = "auth"

    user: Mapped["User"] = relationship(back_populates="auth")

    # TODO Статические методы для получения объектов аутентификации из бд
    
    @staticmethod
    def GBook() -> int:
        return 1
    
    @staticmethod
    def Email() -> int:
        return 2


class Profile(Base):
    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Имя")
    surname: Mapped[str] = mapped_column(String(100), comment="Фамилия")
    patronymic: Mapped[str] = mapped_column(String(100), comment="Отчество")

    __tablename__ = "profile"

    user: Mapped["User"] = relationship(back_populates="profile", uselist=False)

class Role(Base):
    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), comment="Название роли")
    description: Mapped[str] = mapped_column(String(255), comment="Описание роли")

    __tablename__ = "role"

    users: Mapped[List["User"]] = relationship(back_populates="role")

class User(Base):
    id = mapped_column(BigInteger, primary_key=True)
    profile_id = mapped_column(BigInteger, ForeignKey("profile.id"), unique=True, nullable=False, comment="Профиль пользователя")
    role_id = mapped_column(BigInteger, ForeignKey("role.id"), nullable=False, comment="Роль пользователя")

    __tablename__ = "users"

    profile: Mapped["Profile"] = relationship(back_populates="user")
    role: Mapped["Role"] = relationship(back_populates="users")
    auth: Mapped[Optional["Auth"]] = relationship(back_populates="user", uselist=False)
    student_details: Mapped[Optional["StudentDetails"]] = relationship(back_populates="user", uselist=False)
    schedules: Mapped[List["Schedule"]] = relationship(back_populates="student")
    premiums: Mapped[List["Premium"]] = relationship(back_populates="user")
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        back_populates="user",
        foreign_keys="SupportTicket.user_id",
    )
    closed_support_tickets: Mapped[List["SupportTicket"]] = relationship(
        back_populates="closed_by_user",
        foreign_keys="SupportTicket.closed_by_user_id",
    )

class Status(Base):
    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), comment="Название статуса")
    description: Mapped[str] = mapped_column(String(255), comment="Описание статуса")

    __tablename__ = "status"

    student_details: Mapped[List["StudentDetails"]] = relationship(back_populates="status")

class StudentDetails(Base):
    user_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True, comment="Пользователь")
    gradebook_number: Mapped[Integer] = mapped_column(Integer, comment="Номер зачетной книжки")
    status_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey("status.id"), nullable=False, comment="Статус студента")
    daily_limit: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Дневной лимит")
    branch: Mapped[str] = mapped_column(String(255), comment="Филиал")
    faculty: Mapped[str] = mapped_column(String(255), comment="Факультет")
    study_program: Mapped[str] = mapped_column(String(255), comment="Учебная программа")
    current_semester: Mapped[SmallInteger] = mapped_column(SmallInteger, comment="Текущий семестр")
    schedule_send_time: Mapped[Time] = mapped_column(Time, default=time(8, 0), comment="Время отправки расписания")

    __tablename__ = "student_details"

    user: Mapped["User"] = relationship(back_populates="student_details")
    status: Mapped["Status"] = relationship(back_populates="student_details")

class Schedule(Base):
    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True)
    student_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, comment="Студент")
    day_of_week: Mapped[SmallInteger] = mapped_column(SmallInteger, nullable=False, comment="День недели")
    week_type: Mapped[SmallInteger] = mapped_column(SmallInteger, nullable=False, comment="Тип недели")
    file_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="ID Telegram файла с расписанием")

    __tablename__ = "schedule"

    student: Mapped["User"] = relationship(back_populates="schedules")

    # TODO Статические методы для получения week_type (1 & 2)
    # TODO Статические методы для получения day_of_week (1-7)


class Premium(Base):
    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, comment="Пользователь")
    starts_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, comment="Дата начала премиума")
    ends_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, comment="Дата окончания премиума")

    __tablename__ = "premium"

    user: Mapped["User"] = relationship(back_populates="premiums")
    # TODO Статические методы для проверки активности премиума


class SupportTicket(Base):
    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, comment="Пользователь")
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="Сообщение обращения")
    status: Mapped[SmallInteger] = mapped_column(SmallInteger, nullable=False, comment="Статус обращения")
    answer: Mapped[str] = mapped_column(Text, comment="Ответ на обращение")
    closed_by_user_id: Mapped[BigInteger] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True, comment="Пользователь, закрывший обращение")
    closed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), comment="Дата закрытия обращения")

    __tablename__ = "support_ticket"

    user: Mapped["User"] = relationship(
        back_populates="support_tickets",
        foreign_keys=[user_id],
    )
    closed_by_user: Mapped[Optional["User"]] = relationship(
        back_populates="closed_support_tickets",
        foreign_keys=[closed_by_user_id],
    )

    # TODO Статические методы статуса обращения
