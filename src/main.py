import pathlib
import sys

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QDialog

from assets_data import app_icon_png

from i18n import I18n
from settings import load_settings
from theme import apply_theme
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    icon_pix = QPixmap()
    icon_pix.loadFromData(app_icon_png)
    if icon_pix.isNull():
        icon_pix = QPixmap(str(pathlib.Path(__file__).resolve().parent / "assets" / "app_icon.png"))
    app.setWindowIcon(QIcon(icon_pix))

    # Последний выбранный язык и тема восстанавливаются при старте.
    prefs = load_settings()
    i18n = I18n(prefs["lang"])

    # Сохранённая тема применяется ДО показа окна входа: иначе на Windows
    # с тёмной системной темой окно входа рисуется нативно-тёмным (Qt 6.5+
    # сам читает системную тему), даже если выбрана светлая. LoginDialog
    # при создании применит ту же тему ещё раз - безвредно (идемпотентно).
    apply_theme(app, prefs["theme"])

    login = LoginDialog(i18n, initial_theme=prefs["theme"])
    if login.exec() != QDialog.DialogCode.Accepted or login.session is None:
        sys.exit(0)

    # Тема выбрана на окне входа; применяем её ко всему приложению
    # (для тёмной - стиль Fusion, чтобы QSS-стрелки комбо рисовались).
    apply_theme(app, login.session.theme)

    window = MainWindow(login.session, i18n)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
