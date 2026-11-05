"""Эмулятор ONTAP для автономной работы/отладки без реального кластера.

Эмулирует маркеры успеха как у настоящей СХД: volume create отвечает строкой
с 'Successful', lun create - 'Created a LUN of size' (как в оригинальных PS1).
Также эмулирует `igroup show` (доки ONTAP: список initiator groups), чтобы
вкладка Mapping могла подтягивать igroup-ы для комбо выбора.
"""
import re

from backend.base import DEFAULT_TIMEOUT, CommandResult, OntapBackend

# Стартовый набор igroup для эмулятора (в реальной СХД список приходит командой
# `igroup show -vserver svm0 -fields igroup`).
FAKE_IGROUPS = ["ig_linux01", "ig_windows01", "ig_sql01"]


class FakeBackend(OntapBackend):
    def __init__(self):
        self._connected = False
        self.volumes = {}
        self.luns = {}  # path -> {"created": bool, "mappings": [dict]}
        self.igroups = list(FAKE_IGROUPS)

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self, host: str, port: int, username: str, password: str) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def run_command(
        self,
        command: str,
        timeout: float = DEFAULT_TIMEOUT,
        expect: str | None = None,
    ) -> CommandResult:
        if not self._connected:
            raise RuntimeError("Нет активного соединения (эмулятор отключён)")

        cmd = command.strip()
        if cmd.startswith("volume create"):
            output = self._volume_create(cmd)
        elif cmd.startswith("lun create"):
            output = self._lun_create(cmd)
        elif cmd.startswith("lun mapping create"):
            output = self._lun_mapping_create(cmd)
        elif cmd.startswith("lun show"):
            output = self._lun_show(cmd)
        elif cmd.startswith("igroup show"):
            output = self._igroup_show(cmd)
        else:
            output = f"эмулятор: команда получена, поведение не смоделировано:\n{cmd}"

        if expect is not None:
            success = expect in output
            matched = expect if success else None
        else:
            success = True
            matched = None
        return CommandResult(success=success, output=output, matched=matched)

    def _volume_create(self, cmd: str) -> str:
        match = re.search(r"-volume (\S+)", cmd)
        name = match.group(1) if match else "?"
        self.volumes[name] = cmd
        return f"[Job] Job succeeded: Successful\nVolume '{name}' создан (эмулятор)."

    def _lun_create(self, cmd: str) -> str:
        match = re.search(r"-path (\S+)", cmd)
        path = match.group(1) if match else "?"
        size_match = re.search(r"-size (\S+)", cmd)
        size = size_match.group(1) if size_match else ""
        self.luns.setdefault(path, {"created": False, "mappings": []})
        self.luns[path]["created"] = True
        return f"Created a LUN of size {size}.\nLUN '{path}' создан (эмулятор)."

    def _lun_mapping_create(self, cmd: str) -> str:
        lun = self._extract(cmd, "-lun")
        volume = self._extract(cmd, "-volume")
        igroup = self._extract(cmd, "-igroup")
        lun_id = self._extract(cmd, "-lun-id")
        entry = {"volume": volume, "igroup": igroup, "lun_id": lun_id}
        self.luns.setdefault(lun, {"created": False, "mappings": []})
        self.luns[lun]["mappings"].append(entry)
        # Примапили к новому igroup - добавляем в список (как было бы на СХД).
        if igroup and igroup not in self.igroups:
            self.igroups.append(igroup)
        return f"LUN '{lun}' примаплен к igroup '{igroup}' с lun-id {lun_id} (эмулятор)."

    def _lun_show(self, cmd: str) -> str:
        igroup_filter = self._extract(cmd, "-igroup")
        rows = []
        for path, data in self.luns.items():
            for mapping in data["mappings"]:
                if igroup_filter and mapping["igroup"] != igroup_filter:
                    continue
                rows.append(f"{mapping['igroup']:<20}{path:<30}{mapping['lun_id']:<8}")
        if not rows:
            return "Нет примапленных LUN (эмулятор)."
        header = f"{'igroup':<20}{'path':<30}{'lun-id':<8}"
        return header + "\n" + "\n".join(rows)

    def _igroup_show(self, cmd: str) -> str:
        """Имитация реального вывода `igroup show -vserver svm0 -fields igroup`:
        эхо команды в промпте, заголовок-колонка, разделитель, строки
        `svm0    <igroup>`, счётчик строк - как настоящая СХД (C400)."""
        if not self.igroups:
            return (
                "C400::> igroup show -vserver svm0 -fields igroup\n"
                "vserver igroup\n"
                "------- -----------\n"
                "0 entries were displayed."
            )
        lines = [
            "C400::> igroup show -vserver svm0 -fields igroup",
            "vserver igroup      ",
            "------- -----------",
        ]
        lines.extend(f"svm0    {g}" for g in self.igroups)
        lines.append(f"{len(self.igroups)} entries were displayed.")
        return "\n".join(lines)

    @staticmethod
    def _extract(cmd: str, flag: str) -> str:
        match = re.search(re.escape(flag) + r" (\S+)", cmd)
        return match.group(1) if match else ""
