# Строгие параметры кластеров

Источник истины - исходные скрипты в `_reference/`. Значения ниже правятся
только осознанно и с согласованием - это тот самый «строгий» слой.

## Общее (одинаково для C400 и C800)
- vserver: `svm0`
- port: `22`
- Флаги волума: `-security-style ntfs -autosize-mode off -snapshot-policy none -percent-snapshot-space 0`
- Флаги LUN: `-space-reserve disabled -space-allocation enabled`
- Квирк размера волума: **+3%** (`VSize + VSize*3/100`)

## C800 (снято со скрипта v0.6, `_reference/NetApp_Volume_Utility_C800.ps1`)
- host: `0.0.0.0` (в исходнике заглушка - реальный адрес подставляется на месте)
- Аггрегаты: `C800_02_01_SSD_CAP_1`, `C800_02_02_SSD_CAP_1`
- ostype LUN: `windows` (дефолт), `linux`
- QoS-политики (подсказки дословно из `$ShowHelp` исходника):
  - `qos-bronze-svm0`    - 0-234.4Mb/s, 5k IOPs
  - `qos-silver-svm0`    - 0-468.8Mb/s, 7k IOPs
  - `qos-gold-svm0`      - 0-703.2Mb/s, 10k IOPs
  - `qos-platinum-svm0`  - 0-937.5Mb, 20k IOPs
  - `no-qos`             - QoS не используется

## C400 (снято со скрипта v0.6, `_reference/NetApp_Volume_Utility_C400.ps1`)
- host (боевой): `0.0.0.0`  (netapp-c400.example.local)
- host (тестовый, в исходнике закомментирован): `0.0.0.0`
- Аггрегаты: `C400_02_01_SSD_CAP_1`, `C400_02_02_SSD_CAP_1`
- ostype LUN: `windows_gpt` (дефолт), `linux`
- QoS-политики (подсказки дословно из `$ShowHelp` исходника):
  - `qos-bronze-svm0`    - 0-234.4Mb/s, 5k IOPs
  - `qos-silver-svm0`    - 0-468.8Mb/s, 7k IOPs
  - `qos-gold-svm0`      - 0-703.2Mb/s, 10k IOPs
  - `qos-platinum-svm0`  - 0-937.5Mb, 20k IOPs
  - `no-qos`             - QoS не используется

## Заметки
- **ostype per-cluster** (согласовано с оператором 2026-08-16): C400 шлёт
  `windows_gpt`/`linux`, C800 - `windows`/`linux`. Раньше в «Общем» стояло
  `windows/linux` для обоих - это расхождение с C400 закрыто.
- `qos-vip-svm0` в C400.ps1 есть только в тултипах (`$ShowHelp`), радиокнопки
  выбора в UI нет - в рабочий список политик **не входит**.
- Tooltip'ы QoS (Mb/s, IOPs) показываются в UI как подсказка у выбора политики.
- Поведение выбора QoS в UI: по умолчанию стоит `no-qos`, выпадающий список
  заблокирован; рядом чекбокс «разрешить выбирать» (по умолчанию снят) -
  снимает блокировку.
