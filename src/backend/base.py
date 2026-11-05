"""Абстрактный бэкенд ONTAP: Real (paramiko) и Fake (эмулятор) реализуют один и тот же контракт."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Таймаут ожидания ответа СХД - 30 с, как в оригинальных PS1 (send-commands).
DEFAULT_TIMEOUT = 30.0


@dataclass
class CommandResult:
    """Результат выполнения команды на СХД.

    success - найден ли маркер успеха (expect). Для команд без маркера
    (mapping/show) всегда True: там вывод и есть результат.
    output - сырой вывод СХД (эхо команды + ответ + промпт), показывается
    в консоли как есть (живой ответ).
    matched - найденный маркер или None.
    """

    success: bool
    output: str
    matched: str | None = None


class OntapBackend(ABC):
    @abstractmethod
    def connect(self, host: str, port: int, username: str, password: str) -> None:
        """Установить соединение. Бросает исключение при неудаче."""

    @abstractmethod
    def disconnect(self) -> None:
        """Закрыть соединение, если оно открыто."""

    @abstractmethod
    def run_command(
        self,
        command: str,
        timeout: float = DEFAULT_TIMEOUT,
        expect: str | None = None,
    ) -> CommandResult:
        """Отправить команду и дождаться ответа (до timeout секунд).

        Если задан expect - ждать появления этой строки в выводе (маркер
        успеха, как в оригинальных PS1: 'Successful' для volume create,
        'Created a LUN of size' для lun create). Маркер найден -> success=True,
        таймаут -> success=False (вывод всё равно возвращается).
        Без expect -> success=True (вывод и есть результат).
        """

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Активно ли соединение."""
