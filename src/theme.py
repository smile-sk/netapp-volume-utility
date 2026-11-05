"""Темы оформления приложения: светлая (дефолт Qt, пустой QSS) и тёмная.

Выбор делается на окне входа рядом с языком; тема применяется ко всему
приложению через QApplication.setStyleSheet и живёт в Session.theme.

Для тёмной темы дополнительно включается стиль Fusion: нативные стили
Windows (windowsvista/windows11) игнорируют кастомные subcontrol-картинки
QSS (например, QComboBox::down-arrow) - кнопка-квадрат рисуется, а стрелка
нет. Fusion рисует QSS-subcontrol'ы как положено. Светлая тема возвращает
нативный стиль платформы.

ВАЖНО (Qt 6.5+): Qt сам читает системную тему Windows. При тёмной системной
теме нативные виджеты красятся в тёмное даже с пустым QSS - «светлая» тема
приложения выглядела тёмной («две тёмные темы»). Поэтому colorScheme
принудительно фиксируется: светлая тема → Light, тёмная → Dark
(QStyleHints.setColorScheme, доступен с Qt 6.5); для светлой дополнительно
выставляется явная светлая палитра (страховка, если стиль проигнорирует
colorScheme).
"""

import base64
import pathlib
import tempfile

from PySide6.QtCore import Qt

# Светлая стрелка-шеврон для QComboBox::down-arrow.
# В тёмной теме системная стрелка Qt тёмная и сливается с фоном - поэтому
# рисуем свою и кладём PNG рядом с настройками, а QSS ссылается на неё через url().
# ВАЖНО: без явных subcontrol-origin/subcontrol-position нативные стили Windows
# игнорируют image в ::down-arrow - стрелка не рисуется (проверено рендер-тестом).
_COMBO_ARROW_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAAACXBIWXMAAA9hAAAPYQGoP6dpAAABEUlEQVQ4je2QPUvDUBSGn5vGQCedi1BDaSB2cHUT3MTBwR8gtb9D6b/o5NfQ0cFB7CRZncTBNCRcIsW1q4Le9DgJtVxbXTrlGc973gfOgZKSpaFsw6csW/dwOxiuwtB/se0Mh/kGLkcfmLOtZvN1NndsJQ+3IyJdcSRKklFtNk+SUU0ciUSk6+Ee2xxWcaGKPjBGUZ845k5rvfqdPeb52qRiBijqwNhg+jaH9RUAcZZvI3IPVIGouqL2AN4/ZQDsAG+C2m0F/sO/xABxqvdB3QAVBdcAAodAAXKwGTRuf+vOFQM8p7qtUOc/S6odBv7lvJ71x9O0gsYFcDpVOFkk/TMiopI078Wp7onIwitLSpbMFypYXSBjq1ZVAAAAAElFTkSuQmCC"
)

_SETTINGS_DIR = pathlib.Path.home() / ".netapp_volume_utility"


def _combo_arrow_path() -> str:
    """Гарантирует наличие PNG-стрелки и возвращает путь (url()-совместимый, /)."""
    candidates = (_SETTINGS_DIR, pathlib.Path(tempfile.gettempdir()))
    for folder in candidates:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            p = folder / "combo_arrow.png"
            if not p.exists():
                p.write_bytes(base64.b64decode(_COMBO_ARROW_B64))
            return p.as_posix()
        except OSError:
            continue
    # Крайний случай: нет доступа на запись никуда - стрелка просто не рисуется.
    return ""


_ARROW = _combo_arrow_path()

_QSS_TEMPLATE = """
QMainWindow, QDialog, QWidget {
    background-color: #232629;
    color: #e8e8e8;
}

QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #1b1d1f;
    border: 1px solid #3d4044;
    border-radius: 3px;
    padding: 4px 6px;
    color: #e8e8e8;
    selection-background-color: #2d5f8a;
}

QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #4a90d9;
}

QComboBox::drop-down {
    border: none;
    border-left: 1px solid #3d4044;
    background-color: #2b2d30;
    width: 20px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}

QComboBox::drop-down:hover {
    background-color: #3a3d41;
}

QComboBox::drop-down:pressed {
    background-color: #2d5f8a;
}

QComboBox::down-arrow {
    image: url("{ARROW}");
    width: 12px;
    height: 12px;
    subcontrol-origin: padding;
    subcontrol-position: center;
}

QComboBox QAbstractItemView {
    background-color: #2b2d30;
    border: 1px solid #3d4044;
    selection-background-color: #2d5f8a;
    selection-color: #ffffff;
    outline: none;
}

QCheckBox {
    spacing: 6px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #5a5d61;
    border-radius: 3px;
    background-color: #1b1d1f;
}

QCheckBox::indicator:checked {
    background-color: #4a90d9;
    border: 1px solid #4a90d9;
}

QPushButton {
    background-color: #3a3d41;
    border: 1px solid #4a4d52;
    border-radius: 4px;
    padding: 5px 14px;
    color: #e8e8e8;
}

QPushButton:hover { background-color: #45484d; }
QPushButton:pressed { background-color: #2d5f8a; }
QPushButton:disabled { color: #6a6d72; background-color: #2b2d30; }

QTabWidget::pane {
    border: 1px solid #3d4044;
    top: -1px;
}

QTabBar::tab {
    background-color: #2b2d30;
    border: 1px solid #3d4044;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #3a3d41;
    border-bottom: 2px solid #4a90d9;
}

QTabBar::tab:hover:!selected { background-color: #33363a; }

QSplitter::handle { background-color: #3d4044; }
QSplitter::handle:vertical { height: 2px; }

QToolTip {
    background-color: #2b2d30;
    color: #e8e8e8;
    border: 1px solid #4a4d52;
    padding: 4px;
}

QScrollBar:vertical {
    background-color: #232629;
    width: 12px;
}

QScrollBar::handle:vertical {
    background-color: #4a4d52;
    border-radius: 5px;
    min-height: 24px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover { background-color: #5a5d61; }

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background-color: #232629;
    height: 12px;
}

QScrollBar::handle:horizontal {
    background-color: #4a4d52;
    border-radius: 5px;
    min-width: 24px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover { background-color: #5a5d61; }

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QTableWidget, QTableView {
    background-color: #1b1d1f;
    alternate-background-color: #232629;
    gridline-color: #3d4044;
    border: 1px solid #3d4044;
}

QHeaderView::section {
    background-color: #33363a;
    border: 1px solid #3d4044;
    padding: 4px 8px;
    color: #e8e8e8;
}
"""

if _ARROW:
    # ВАЖНО: в шаблоне кавычки вокруг {ARROW} уже есть - добавлять свои
    # НЕЛЬЗЯ, иначе получится url(""путь"") и Qt не загрузит картинку.
    DARK_QSS = _QSS_TEMPLATE.replace("{ARROW}", _ARROW)
else:
    DARK_QSS = _QSS_TEMPLATE.replace('image: url("{ARROW}");\n', "")

LIGHT_QSS = ""

THEMES = {
    "light": LIGHT_QSS,
    "dark": DARK_QSS,
}

# Порядок показа в комбо на окне входа (подписи берутся из i18n: theme_light/theme_dark).
THEME_KEYS = ("light", "dark")

# Нативный стиль платформы, запоминается при первом применении темы
# (objectName(): "windows11"/"windowsvista" на Windows, "fusion" на Linux и т.п.).
_DEFAULT_STYLE: str | None = None


def apply_theme(app, theme: str) -> None:
    """Применяет тему ко всему приложению.

    Тёмная тема дополнительно включает стиль Fusion: нативные стили Windows
    игнорируют кастомные subcontrol-картинки QSS (стрелка комбо не рисуется),
    Fusion рисует их как положено. Светлая тема возвращает нативный стиль.

    ВАЖНО (Qt 6.5+): Qt сам читает системную тему Windows, и при тёмной
    системной теме нативные виджеты красятся в тёмное даже с пустым QSS -
    «светлая» тема приложения выглядела тёмной (две тёмные темы).
    Поэтому colorScheme принудительно фиксируется: светлая тема → Light,
    тёмная → Dark (QStyleHints.setColorScheme, доступен с Qt 6.5).
    Для светлой дополнительно выставляется явная светлая палитра -
    страховка, если стиль проигнорирует colorScheme.
    """
    global _DEFAULT_STYLE
    if _DEFAULT_STYLE is None:
        _DEFAULT_STYLE = app.style().objectName()
    hints = app.styleHints()
    if theme == "dark":
        hints.setColorScheme(Qt.ColorScheme.Dark)
        if app.style().objectName() != "fusion":
            app.setStyle("Fusion")
        app.setStyleSheet(DARK_QSS)
    else:
        hints.setColorScheme(Qt.ColorScheme.Light)
        if _DEFAULT_STYLE and app.style().objectName() != _DEFAULT_STYLE:
            app.setStyle(_DEFAULT_STYLE)
        app.setStyleSheet(LIGHT_QSS)
        # Явная светлая палитра: нативный стиль (windows11) при системной
        # тёмной теме рисует виджеты тёмными, полагаясь на палитру.
        app.setPalette(app.style().standardPalette())
