"""Сборка команд ONTAP из строгого слоя (app_config). Единственное место, где
командные строки формируются - UI сюда только передаёт введённые значения.

Также здесь живут маркеры успеха в выводе СХД (как $prompt в оригинальных
PS1 send-commands): volume create отвечает 'Successful', lun create -
'Created a LUN of size'. Backend ждёт эти строки с таймаутом и по ним
определяет успех/ошибку.

Размеры - строго по официальной документации ONTAP (docs.netapp.com, v9.19.1),
правила одинаковы для обоих кластеров (C400 и C800 - ONTAP):
  - volume create -size {<integer>[KB|MB|GB|TB|PB]} - только целое + единица,
    минимум FlexVol 20 MB;
  - lun create -size - целое число байт с однобуквенным суффиксом-множителем
    (c/w/B/k/M/G/T).
Оригинальные PS1 в этом вопросе НЕ эталон (там float / сырая строка без
валидации) - по решению оператора 2026-08-16 размеры проверяются по докам.

Квирк +3% для volume (VSize + VSize*3/100) округляется ВВЕРХ до целого:
гарантия «как минимум +3%» при целочисленном -size (33 -> 33.99 -> 34GB).
"""
import math

from app_config import VSERVER, VOLUME_FLAGS, LUN_FLAGS, VOLUME_SIZE_QUIRK_PERCENT

VOLUME_CREATE_OK_MARKER = "Successful"
LUN_CREATE_OK_MARKER = "Created a LUN of size"


def apply_volume_size_quirk(size_value: int) -> int:
    """+3% к размеру volume с округлением вверх до целого.

    Доки ONTAP: -size принимает <integer>... - дробное значение недопустимо.
    ceil гарантирует запас как минимум +3% и целое число (33 -> 33.99 -> 34).
    """
    v_size = int(size_value)
    return math.ceil(v_size * (1.0 + VOLUME_SIZE_QUIRK_PERCENT / 100.0))


def build_volume_create(name: str, size_value: int, size_unit: str, aggregate: str, qos_policy: str) -> str:
    real_size = apply_volume_size_quirk(size_value)
    cmd = (
        f"volume create -vserver {VSERVER} -volume {name} -aggregate {aggregate} "
        f"-size {real_size}{size_unit} {VOLUME_FLAGS}"
    )
    if qos_policy and qos_policy != "no-qos":
        cmd += f" -qos-policy-group {qos_policy}"
    return cmd


def build_lun_create(name: str, size_value: int, size_unit: str, ostype: str) -> str:
    path = f"/vol/{name}/{name}"
    return (
        f"lun create -vserver {VSERVER} -path {path} "
        f"-size {size_value}{size_unit} -ostype {ostype} {LUN_FLAGS}"
    )


def build_lun_mapping_create(lun: str, volume: str, igroup: str, lun_id: str) -> str:
    return f"lun mapping create -lun {lun} -volume {volume} -igroup {igroup} -lun-id {lun_id}"


def build_lun_show(igroup: str = "") -> str:
    igroup = (igroup or "").strip()
    if igroup:
        return f"lun show -igroup {igroup} -m"
    return "lun show -m"


def build_igroup_show() -> str:
    """Список igroup одним вызовом (доки ONTAP 9.19.1: `igroup show`, оно же
    `lun igroup show` - в примере доков именно `igroup show -instance`).
    `-fields igroup` даёт только имена - компактный вывод для комбо.
    """
    return f"igroup show -vserver {VSERVER} -fields igroup"


def parse_igroup_names(output: str) -> list[str]:
    """Достаёт имена igroup из вывода `igroup show ...`.

    Реальный вывод ONTAP (`igroup show -vserver svm0 -fields igroup`) - ДВЕ
    колонки, имя igroup ВТОРОЕ (последнее), vserver первое:
        C400::> igroup show -vserver svm0 -fields igroup
        vserver igroup
        ------- -----------
        svm0    CL-MAIN-D01
        svm0    CL-MAIN-P01-Cloud
    Позиция колонки имени определяется по заголовку таблицы.

    Поддерживаются также:
      - одноколоночный вывод (заголовок `igroup`) - как у эмулятора;
      - полная таблица (`igroup proto data type vserver`) - имя igroup первым.

    Пропускаются: эхо команды в промпте (в т.ч. без промпта - по флагам -...),
    заголовок таблицы, разделители колонок (---) и строка
    'N entries were displayed'.
    """
    names: list[str] = []
    igroup_first = True  # позиция имени: первая (полная таблица / одна колонка)
    for raw in output.splitlines():
        line = raw.strip()
        if not line or "entries were displayed" in line:
            continue
        tokens = line.split()
        if not tokens:
            continue
        if all(t.startswith("-") for t in tokens):
            continue  # разделитель колонок (-------)
        if "::>" in line:
            continue  # эхо команды в промпте (C400::> igroup show ...)
        if any(t.startswith("-") and len(t) > 1 for t in tokens):
            continue  # эхо команды без промпта (флаги -vserver -fields ...)
        if "igroup" in tokens:
            # заголовок: `igroup` | `vserver igroup` | `igroup proto data type vserver`
            igroup_first = tokens[0] == "igroup"
            continue
        name = tokens[0] if igroup_first else tokens[-1]
        if name:
            names.append(name)
    return names
