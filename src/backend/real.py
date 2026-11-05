"""Боевой бэкенд: интерактивная SSH-сессия к кластеру NetApp через paramiko.

Держит один открытый shell-канал на всё время работы приложения (в отличие от
эталонных PS1-скриптов, которые открывали новую SSH-сессию на каждое действие) -
это и даёт «живую консоль» снизу окна.

Ответ ловится как в оригинальных скриптах: run_command() умеет ждать текстовый
маркер успеха (expect), например 'Successful' для volume create или
'Created a LUN of size' для lun create - таймаут 30 с (как $Stream.expect
в PS1 send-commands). Маркер найден -> success=True; таймаут -> success=False
(сырой вывод всё равно возвращается, чтобы консоль показывала ответ как есть).

ВАЖНО (QA-024, фикс v0.1.8): при ожидании маркера НЕ выходим по «тишине» -
ждём маркер до дедлайна (30 с), как эталон. Эвристика «1 с тишины» осталась
только для expect=None (mapping/show/живая консоль), где вывода и есть результат.
Раньше break по тишине >1 с давал ложный success=False на медленной СХД:
команда реально выполнялась, но маркер, пришедший позже, не дожидался.

ВАЖНО (QA-030, фикс v0.1.18): ONTAP читает размер терминала ПРИ СОЗДАНИИ pty
(pty-req), а последующие window-change (resize_pty) игнорирует. Поэтому ширину
задаём прямо в invoke_shell(width=..., height=...) - иначе остаются 80 колонок,
и длинные строки 'lun show -m' переносятся, превращая таблицу в кашу.
Дополнительно: 'set -pager off' (работает на C400) и документированный
'set -rows 0' (офиц. доки ONTAP: '0' отключает паузу) - страховка от пейджера.
"""
import time

import paramiko

from backend.base import DEFAULT_TIMEOUT, CommandResult, OntapBackend

# Добор хвоста после найденного маркера (промпт/остаток вывода для консоли).
_TAIL_DRAIN = 0.5
# Размер псевдотерминала: задаётся В pty-req (см. QA-030) - ONTAP не уважает
# поздний resize_pty, поэтому 80x24 из дефолта превращает вывод в кашу.
_PTY_WIDTH = 512
_PTY_HEIGHT = 5000


class RealBackend(OntapBackend):
    def __init__(self):
        self._client = None
        self._shell = None

    @property
    def connected(self) -> bool:
        if self._client is None:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    def connect(self, host: str, port: int, username: str, password: str) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            host,
            port=port,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=15,
        )
        # Ширина/высота ДОЛЖНЫ быть в pty-req при создании shell - ONTAP
        # читает размер терминала именно там (QA-030).
        shell = client.invoke_shell(width=_PTY_WIDTH, height=_PTY_HEIGHT)
        time.sleep(0.5)
        if shell.recv_ready():
            shell.recv(65535)
        # Пейджер off: 'set -pager off' (проверено на C400) + документированный
        # 'set -rows 0' (офиц. доки: '0' disables) - на случай, если кластер
        # всё же решит пагинировать длинный вывод.
        shell.send("set -pager off\n")
        time.sleep(0.5)
        while shell.recv_ready():
            shell.recv(65535)
        shell.send("set -rows 0\n")
        time.sleep(0.5)
        while shell.recv_ready():
            shell.recv(65535)
        # Дополнительная страховка на случай, если конкретная версия ONTAP
        # всё-таки реагирует на window-change (вреда не принесёт).
        try:
            shell.resize_pty(width=_PTY_WIDTH, height=_PTY_HEIGHT)
        except Exception:
            pass
        self._client = client
        self._shell = shell

    def disconnect(self) -> None:
        if self._shell is not None:
            try:
                self._shell.close()
            except Exception:
                pass
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._shell = None
        self._client = None

    def run_command(
        self,
        command: str,
        timeout: float = DEFAULT_TIMEOUT,
        expect: str | None = None,
    ) -> CommandResult:
        if not self.connected or self._shell is None:
            raise RuntimeError("Нет активного SSH-соединения")

        self._shell.settimeout(0.5)
        self._shell.send(command + "\n")

        chunks = []
        buffer = ""
        deadline = time.time() + timeout
        idle_since = None
        matched = None
        while time.time() < deadline:
            if self._shell.recv_ready():
                chunks.append(self._shell.recv(65535).decode(errors="replace"))
                buffer = "".join(chunks)
                idle_since = time.time()
                if expect is not None and matched is None and expect in buffer:
                    matched = expect
                    # Маркер найден: короткий добор хвоста, чтобы консоль
                    # показала полный ответ (промпт и т.п.). Дедлайн не
                    # продлевается - ждём только пока данные реально идут.
                    tail_deadline = time.time() + _TAIL_DRAIN
                    while time.time() < tail_deadline:
                        if self._shell.recv_ready():
                            chunks.append(self._shell.recv(65535).decode(errors="replace"))
                            buffer = "".join(chunks)
                            tail_deadline = time.time() + _TAIL_DRAIN
                        else:
                            time.sleep(0.05)
                    break
            else:
                # Эвристика «1 с тишины» - ТОЛЬКО для свободного вывода
                # (expect=None): mapping/show/живая консоль. При ожидании
                # маркера тишина не прерывает цикл - ждём до deadline,
                # как $Stream.expect в оригинальных PS1 (30 с).
                if expect is None and idle_since is not None and time.time() - idle_since > 1.0:
                    break
                time.sleep(0.05)

        if expect is not None:
            success = matched is not None
        else:
            success = True
        return CommandResult(success=success, output=buffer, matched=matched)
