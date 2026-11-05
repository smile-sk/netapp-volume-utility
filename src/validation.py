"""Валидация ввода: имена Volume/LUN и размеры.

Имена - строго по офиц. правилам NetApp (KB «Can a NetApp volume name contain a
hyphen or dash», ONTAP 9; docs.netapp.com, lun-create v9.19.1):
  - Volume: имя начинается с латинской буквы (a-z/A-Z), далее - буквы/цифры/
    подчёркивание, максимум 203 символа (FlexVol). Дефис НЕ разрешён.
  - LUN: доки допускают также «-», «{», «}», «.» (макс. 255), но по SPEC.md и
    решению оператора (QA-022) пробелы и служебные символы запрещены для обоих
    типов имён - расхождение с доками LUN сознательное (см. README).
Итоговое правило для обоих типов: `^[A-Za-z][A-Za-z0-9_]{2,202}$`
(минимум 3 символа - по SPEC.md).

Размер: только целые положительные числа - строго по официальной документации
ONTAP (docs.netapp.com, v9.19.1), правила одинаковы для обоих кластеров:
  - `volume create -size {<integer>[KB|MB|GB|TB|PB]}` - только целое + единица,
    минимум FlexVol 20 MB;
  - `lun create -size` - целое число байт с однобуквенным суффиксом-множителем
    (c/w/B/k/M/G/T).
Дробные, ноль и отрицательные не документированы - отклоняются до отправки на СХД.
Единицы в UI - только GB/TB, поэтому минимум 20 MB удовлетворяется автоматически
(любое целое >= 1 GB > 20 MB). Оригинальные PS1 здесь НЕ эталон (решение оператора).
"""
import re

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,202}$")
_SIZE_RE = re.compile(r"^\d+$")
_NAME_MAX = 203


def validate_name(name: str):
    """Возвращает (ok: bool, error_key: str | None).

    Правило (доки ONTAP + SPEC.md, QA-022): имя начинается с латинской буквы,
    дальше - латинские буквы/цифры/подчёркивание; без пробелов, дефисов,
    кириллицы и прочих спецсимволов; длина 3..203 символа.
    Функция самодостаточна: ведущие/хвостовые пробелы защёлкиваются внутри,
    поэтому прямой вызов validate_name(' 1abc') тоже корректен (QA-021).
    """
    name = (name or "").strip()
    if len(name) < 3:
        return False, "err_name_too_short"
    if len(name) > _NAME_MAX:
        return False, "err_name_too_long"
    if not name[0].isascii() or not name[0].isalpha():
        # Первый символ не латинская буква (цифра, _, кириллица, пробел...).
        return False, "err_name_start"
    if not _NAME_RE.match(name):
        # Первый символ ок, но дальше есть запрещённый (дефис, пробел, точка...).
        return False, "err_name_chars"
    return True, None


def validate_size(text: str):
    """Размер - целое положительное число.

    Доки ONTAP: volume -size <integer>[KB|MB|GB|TB|PB], lun -size - целое
    число байт с суффиксом-множителем (c/w/B/k/M/G/T). Дробные/ноль/минус
    недокументированы и отклоняются.
    Возвращает (ok: bool, value_or_error_key: int | str).
    """
    s = (text or "").strip()
    if not _SIZE_RE.match(s):
        return False, "err_size_invalid"
    value = int(s)
    if value <= 0:
        return False, "err_size_invalid"
    return True, value
