"""Точка входа для сборки standalone exe (PyInstaller --onefile).

Запуск из исходников: python src\build_main.py - то же самое, что main.py.

Ассеты (логотип входа, иконка) вшиты в код через assets_data.py (base64) -
exe полностью автономен и не зависит от файлов на диске и от venv проекта.
paramiko собирается внутрь из окружения сборки (см. docs в README).
"""
import main  # noqa: E402

if __name__ == "__main__":
    main.main()
