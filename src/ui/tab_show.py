"""Вкладка «Показать» (как TabPage_FreeLun в оригинальных PS1).

Две команды, дословно по образцам _reference/*.ps1 (C400.ps1:755, C400.ps1:790):
  - по igroup:  lun show -igroup <igroup> -m   (кнопка «Показать по igroup»)
  - все примапленные: lun show -m              (кнопка «Показать все»)
Команды собираются ТОЛЬКО в ontap_commands.build_lun_show() - здесь только
передача введённого значения. Вывод СХД показывается как есть (фильтр-маркер
не ищется): для show вывод и есть результат.
"""
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QLabel,
    QMessageBox,
)

from ontap_commands import build_lun_show


class ShowTab(QWidget):
    def __init__(self, session, i18n, log_callback, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.log = log_callback

        self.igroup_edit = QLineEdit()

        show_igroup_btn = QPushButton(i18n.t("btn_show_igroup"))
        show_igroup_btn.clicked.connect(self._on_show_igroup)
        show_all_btn = QPushButton(i18n.t("btn_show_all"))
        show_all_btn.clicked.connect(self._on_show_all)

        self.result_view = QPlainTextEdit()
        self.result_view.setReadOnly(True)

        form = QFormLayout()
        form.addRow(i18n.t("lbl_igroup"), self.igroup_edit)

        btn_row = QHBoxLayout()
        btn_row.addWidget(show_igroup_btn)
        btn_row.addWidget(show_all_btn)
        btn_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btn_row)
        layout.addWidget(QLabel(i18n.t("lbl_result")))
        layout.addWidget(self.result_view)

    def _on_show_igroup(self):
        # Команда: lun show -igroup <igroup> -m (образец C400.ps1:755).
        self._run(build_lun_show(self.igroup_edit.text().strip()))

    def _on_show_all(self):
        # Команда: lun show -m (образец C400.ps1:790).
        self._run(build_lun_show(""))

    def _run(self, command: str):
        confirm = QMessageBox.question(
            self, self.i18n.t("confirm_title"), f"{self.i18n.t('confirm_text')}\n\n{command}"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # Как в оригинале: вывод lun show и есть результат, маркер не ищем.
        self.log(f"> {command}")
        try:
            result = self.session.backend.run_command(command)
        except Exception as exc:
            self.log(f"[!] {exc}", level="error")
            QMessageBox.critical(self, self.i18n.t("err_title"), str(exc))
            return

        self.log(result.output)
        self.result_view.setPlainText(result.output)
