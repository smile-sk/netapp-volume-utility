"""
Строгий слой параметров ONTAP. Источник истины - docs/SPEC.md и config/clusters.md.
Бизнес-логика и UI берут значения только отсюда, руками командные строки не собирают.
"""
from dataclasses import dataclass

VSERVER = "svm0"
SSH_PORT = 22

VOLUME_FLAGS = "-security-style ntfs -autosize-mode off -snapshot-policy none -percent-snapshot-space 0"
LUN_FLAGS = "-space-reserve disabled -space-allocation enabled"

# Квирк размера волума: +3% (VSize + VSize*3/100), считается как float.
VOLUME_SIZE_QUIRK_PERCENT = 3.0

SIZE_UNITS = ("GB", "TB")

TARGETS = ("PROD", "TEST")


@dataclass(frozen=True)
class QosPolicy:
    name: str
    hint: str


@dataclass(frozen=True)
class ClusterConfig:
    key: str
    display_name: str
    hosts: dict  # {"PROD": "...", "TEST": "..."}
    aggregates: tuple
    lun_ostypes: tuple  # значения -ostype именно этого кластера (эталон: C400.ps1 / C800.ps1)
    qos_policies: tuple  # QosPolicy, "no-qos" всегда последним


# Набор QoS и подсказки - дословно из исходных скриптов (_reference/*.ps1, $ShowHelp).
_COMMON_QOS = (
    QosPolicy("qos-bronze-svm0", "0-234.4Mb/s, 5k IOPs"),
    QosPolicy("qos-silver-svm0", "0-468.8Mb/s, 7k IOPs"),
    QosPolicy("qos-gold-svm0", "0-703.2Mb/s, 10k IOPs"),
    QosPolicy("qos-platinum-svm0", "0-937.5Mb, 20k IOPs"),
)

NO_QOS = QosPolicy("no-qos", "QoS не используется")

# Примечание: qos-vip-svm0 в C400.ps1 есть только в тултипах ($ShowHelp),
# радиокнопки выбора нет - в рабочий список политик не входит.
CLUSTERS = {
    "C400": ClusterConfig(
        key="C400",
        display_name="C400_02",
        hosts={"PROD": "0.0.0.0", "TEST": "0.0.0.0"},
        aggregates=("C400_02_01_SSD_CAP_1", "C400_02_02_SSD_CAP_1"),
        # эталон прежних скриптов (кластер C400): дефолт windows_gpt, дальше linux
        lun_ostypes=("windows_gpt", "linux"),
        qos_policies=_COMMON_QOS + (NO_QOS,),
    ),
    "C800": ClusterConfig(
        key="C800",
        display_name="C800_02",
        # clusters.md: host в исходнике заглушка (0.0.0.0) - реальный адрес подставляется
        # на месте; отдельный тестовый IP для C800 в конфиге не задокументирован.
        hosts={"PROD": "0.0.0.0", "TEST": "0.0.0.0"},
        aggregates=("C800_02_01_SSD_CAP_1", "C800_02_02_SSD_CAP_1"),
        # эталон прежних скриптов (кластер C800): дефолт windows, дальше linux
        lun_ostypes=("windows", "linux"),
        qos_policies=_COMMON_QOS + (NO_QOS,),
    ),
}
