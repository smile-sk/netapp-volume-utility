"""Живая SSH-консоль снизу окна: свободный ввод команд напрямую в backend,
плюс лог результатов структурированных действий со вкладок.

Уровни вывода: info (обычный текст), success (зелёный), error (красный).
Факт успеха/ошибки подсвечивается цветом как визуальное удобство, при этом
сырой ответ СХД всегда показывается как есть (живой ответ).

ВАЖНО (QA-030): виджет переведён в режим NoWrap - иначе длинные строки
'vserver show'/'lun show -m' софт-рапятся по ширине окна, и таблица
визуально превращается в кашу (горизонтальный скролл вместо переноса).
"""
import html

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QLineEdit

COLOR_SUCCESS = "#2e9e4f"
COLOR_ERROR = "#e53935"


class ConsoleWidget(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n

        self.title_label = QLabel(i18n.t("console_title"))
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(5000)
        # QA-030: длинные строки НЕ переносим - каждая строка вывода остаётся
        # целой, при необходимости появляется горизонтальный скролл.
        self.output.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.input = QLineEdit()
        self.input.returnPressed.connect(self._on_enter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.title_label)
        layout.addWidget(self.output)
        layout.addWidget(self.input)

    def log(self, text: str, level: str = "info"):
        if not text:
            return
        if level == "success":
            self.output.appendHtml(
                f'<span style="color:{COLOR_SUCCESS};">{html.escape(text)}</span>'
            )
        elif level == "error":
            self.output.appendHtml(
                f'<span style="color:{COLOR_ERROR};">{html.escape(text)}</span>'
            )
        else:
            self.output.appendPlainText(text)

    def _on_enter(self):
        cmd = self.input.text().strip()
        if not cmd:
            return
        self.input.clear()
        self.log(f"> {cmd}")
        try:
            result = self.session.backend.run_command(cmd)
            self.log(result.output)
        except Exception as exc:
            self.log(f"[!] {exc}", level="error")
