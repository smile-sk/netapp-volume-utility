# Спецификация операций (эталон - из C800-скрипта)

Транспорт: SSH к кластеру (Posh-SSH), порт 22, логин интерактивно (Get-Credential).
Перед каждой командой - подтверждение готовой строки оператором.
Всё жёстко под `-vserver svm0`.

## 1. Создать волум
```
volume create -vserver svm0 -volume <имя> -aggregate <аггр> -size <размер><ед>
  -security-style ntfs -autosize-mode off -snapshot-policy none -percent-snapshot-space 0
  [-qos-policy-group <qos>]
```
- КВИРК: запрошенный размер увеличивается на +3% (`VSize + VSize*3/100`) - запас под оверхед.
- Строгие флаги: `security-style ntfs`, `autosize-mode off`, `snapshot-policy none`,
  `percent-snapshot-space 0`.

## 2. Создать LUN
```
lun create -vserver svm0 -path <имя> -size <размер><ед> -ostype <windows|linux>
  -space-reserve disabled -space-allocation enabled
```

## 3. Примапить LUN
```
lun mapping create -lun <> -volume <> -igroup <> -lun-id <>
```

## 4. Показать луны
```
lun show -igroup <> -m      # свободные по igroup
lun show -m                 # все
```

## Что считается «строгим» (трогать нельзя без согласования)
SVM (`svm0`), имена аггрегатов, QoS-политики, наборы флагов волума и луна.
Именно этот слой отличает C400 от C800.
