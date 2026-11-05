# Сборка EXE (NetAppVolumeUtility) - процесс для разработчика

Цель: собрать автономный `src/NetAppVolumeUtility.exe` (один файл, без консоли,
с иконкой). Проверенный процесс (архитектор Cody, 2026-08-18) - одним прогоном,
без пересборок. История ошибок, которых здесь удалось избежать, - в CHANGELOG
(0.1.15, 0.1.16, build 2026-08-18).

## Окружение (не менять!)
- PyInstaller 6.21.0 + paramiko 5.0.0 + PySide6 - в venv ai_ui (Python 3.12.10):
  `D:\Documents\Projects\ai_ui\venv`
- **НЕ использовать `.venv` проекта (Python 3.14):** C-расширения paramiko
  (cryptography/_cffi_backend) несовместимы по ABI → `ModuleNotFoundError:
  No module named '_cffi_backend'` (история: 0.1.15).
- Ассеты (логотип входа, иконка) вшиты в код через `src/assets_data.py` (base64) -
  exe не зависит от файлов на диске и от `__file__`-путей в frozen-режиме.

## Иконка - только .ico
- PyInstaller на Windows принимает `--icon .ico` (или `.exe`). **PNG не подходит:**
  без Pillow сборка падает `ValueError` (история: первая сборка бюджета -
  передали `src\assets\app_icon.png`).
- Рабочий файл: `_TEMP/app_icon.ico`.

## Главный подводный камень: таймаут 120 c
- Среда агентов (`run_python`) жёстко режет процесс через **120 секунд**, а сборка
  PySide6 идёт ~220-270 c. Прямой вызов PyInstaller из `run_python` убьёт сборку
  на «Fixing EXE headers» - exe не допишется (история: оборванная сборка,
  exe исчез).
- Решение: запускать PyInstaller **фоновым процессом** (Popen без ожидания) - он
  переживёт завершение `run_python`; прогресс смотреть по логу и появлению exe.

## Проверенный рецепт (один прогон, ~4 мин)
1. Убедиться, что иконка на месте: `_TEMP\app_icon.ico`.
2. Собрать из `run_python` (Windows-хост) фоном:
   ```python
   import subprocess, os
   root = r"D:\Documents\Projects\NetAppVolumeUtility"
   cmd = [
       r"D:\Documents\Projects\ai_ui\venv\Scripts\python.exe", "-m", "PyInstaller",
       "--noconfirm", "--onefile", "--windowed",
       "--icon", os.path.join(root, "_TEMP", "app_icon.ico"),
       "--name", "NetAppVolumeUtility",
       "--distpath", os.path.join(root, "src"),
       "--workpath", os.path.join(root, "_TEMP", "build"),
       "--specpath", os.path.join(root, "_TEMP"),
       os.path.join(root, "src", "main.py"),
   ]
   log = open(os.path.join(root, "_TEMP", "kodi_build.log"), "w", encoding="utf-8")
   subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=root)
   ```
   Точка входа - `src/main.py`; `src/build_main.py` лишь импортирует `main.main()`.
3. Ждать `Build complete!` в логе (или появления exe в `src\`). Это ~4 минуты.
4. Проверить результат:
   - exe существует, размер ~52.8 МБ;
   - иконка вшита: `ExtractIconEx` возвращает >=1 иконку (WinAPI);
   - в логе нет ERROR / ValueError.
5. Прибрать: удалить `_TEMP\build\` и `_TEMP\NetAppVolumeUtility.spec` (мусор
   повторной сборки). Лог сборки оставить - это история.

## Чек-лист перед сборкой
- [ ] CHANGELOG.md и state/developer.json отражают актуальное состояние (иначе
      в exe уедет недокументированное поведение).
- [ ] smoke-тест зелёный: `.venv\Scripts\python.exe _TEMP\smoke_test.py`
      (внимание: это .venv ПРОЕКТА, для теста; для СБОРКИ - venv ai_ui).
- [ ] есть отмашка оператора на пересборку (правило проекта).
- [ ] версия в state/developer.json совпадает с тем, что собираем.

## Чего НЕ делать
- Не собирать «описанием» - только реальным прогоном; результат проверять
  по файлу exe, а не по словам.
- Не передавать PNG в `--icon`.
- Не собирать из `.venv` проекта (Python 3.14, ABI-несовместим).
- Не запускать PyInstaller в `run_python` напрямую (таймаут 120 c).
- Не собирать без `--windowed` (появится консоль) и без `--icon`.
