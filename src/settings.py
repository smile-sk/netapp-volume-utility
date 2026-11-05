"""Пользовательские настройки, переживающие перезапуск: язык, тема,
чекбокс «Повторить имя и размер» (Volume → LUN) и адреса кластеров
(переопределение PROD/TEST - чтобы не вшивать адрес в exe).

Хранятся в <домашний каталог>/.netapp_volume_utility/settings.json.
Учётные данные сюда НЕ попадают по определению - только безобидные
UI-предпочтения (последний выбранный язык, тема, состояние чекбокса,
переопределения адресов).
"""
import json
from pathlib import Path

DEFAULT_LANG = "ru"
DEFAULT_THEME = "light"
DEFAULT_REPEAT = True  # «Повторить имя и размер с вкладки Volume» - по умолчанию отмечен
KNOWN_LANGS = ("ru", "ua", "en")
KNOWN_THEMES = ("light", "dark")
KNOWN_TARGETS = ("PROD", "TEST")

DEFAULT_PATH = Path.home() / ".netapp_volume_utility" / "settings.json"


def default_settings() -> dict:
    return {"lang": DEFAULT_LANG, "theme": DEFAULT_THEME, "repeat_vol_to_lun": DEFAULT_REPEAT, "hosts": {}}


def _clean_hosts(raw: dict) -> dict:
    """Оставляет валидные переопределения адресов: {кластер: {PROD|TEST: строка}}.
    Пустые/не-строки отбрасываются; несуществующие цели игнорируются."""
    out = {}
    for cluster_key, targets in raw.items():
        if not isinstance(targets, dict):
            continue
        clean = {}
        for target, host in targets.items():
            if target in KNOWN_TARGETS and isinstance(host, str) and host.strip():
                clean[target] = host.strip()
        if clean:
            out[cluster_key] = clean
    return out


def load_settings(path: Path | None = None) -> dict:
    """Читает настройки; при отсутствии файла или повреждённом JSON
    возвращает дефолты. Неизвестные значения отбрасываются."""
    prefs = default_settings()
    p = path or DEFAULT_PATH
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        lang = raw.get("lang", DEFAULT_LANG)
        theme = raw.get("theme", DEFAULT_THEME)
        repeat = raw.get("repeat_vol_to_lun", DEFAULT_REPEAT)
        hosts_raw = raw.get("hosts")
        if lang in KNOWN_LANGS:
            prefs["lang"] = lang
        if theme in KNOWN_THEMES:
            prefs["theme"] = theme
        if isinstance(repeat, bool):
            prefs["repeat_vol_to_lun"] = repeat
        if isinstance(hosts_raw, dict):
            prefs["hosts"] = _clean_hosts(hosts_raw)
    except (OSError, ValueError, TypeError):
        pass
    return prefs


def save_settings(
    lang: str | None = None,
    theme: str | None = None,
    path: Path | None = None,
    repeat_vol_to_lun: bool | None = None,
    hosts: dict | None = None,
) -> bool:
    """Пишет настройки атомарно (tmp + replace), чтобы не оставить битый файл.

    Переданные значения объединяются с уже сохранёнными (можно обновить
    одно поле, не трогая остальные). Возвращает True при успехе.

    ВНИМАНИЕ: `path` - третий позиционный аргумент (совместимость со старой
    сигнатурой save_settings(lang, theme, path)); repeat_vol_to_lun и hosts -
    только по ключу. Раньше вставка repeat на третью позицию ломала позиционные
    вызовы (путь уходил в repeat_vol_to_lun и писался дефолтный файл).
    """
    p = path or DEFAULT_PATH
    try:
        prefs = load_settings(p)
        if lang is not None and lang in KNOWN_LANGS:
            prefs["lang"] = lang
        if theme is not None and theme in KNOWN_THEMES:
            prefs["theme"] = theme
        if repeat_vol_to_lun is not None:
            prefs["repeat_vol_to_lun"] = bool(repeat_vol_to_lun)
        if hosts is not None and isinstance(hosts, dict):
            merged = dict(prefs.get("hosts", {}))
            for ck, targets in _clean_hosts(hosts).items():
                merged[ck] = {**merged.get(ck, {}), **targets}
            prefs["hosts"] = merged
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(prefs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(p)
        return True
    except OSError:
        return False
