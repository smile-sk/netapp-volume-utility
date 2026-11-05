from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QCheckBox,
    QMessageBox,
)

from app_config import SIZE_UNITS
from backend.base import DEFAULT_TIMEOUT
from ontap_commands import VOLUME_CREATE_OK_MARKER, build_volume_create
from validation import validate_name, validate_size


class VolumeTab(QWidget):
    def __init__(self, session, i18n, log_callback, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.log = log_callback

        self.name_edit = QLineEdit()
        self.size_edit = QLineEdit()
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(list(SIZE_UNITS))

        self.aggregate_combo = QComboBox()
        self.aggregate_combo.addItems(list(session.cluster.aggregates))

        self.qos_hints = {q.name: q.hint for q in session.cluster.qos_policies}
        self.qos_combo = QComboBox()
        for qos in session.cluster.qos_policies:
            self.qos_combo.addItem(qos.name)
        no_qos_index = self.qos_combo.findText("no-qos")
        if no_qos_index >= 0:
            self.qos_combo.setCurrentIndex(no_qos_index)
        # По умолчанию QoS не выбирается: комбо заблокировано, стоит no-qos.
        self.qos_combo.setEnabled(False)
        self.qos_combo.currentTextChanged.connect(self._update_qos_tooltip)
        self._update_qos_tooltip(self.qos_combo.currentText())

        # Чекбокс снимает блокировку выбора QoS (по умолчанию снят).
        self.qos_enable_cb = QCheckBox(i18n.t("lbl_qos_enable"))
        self.qos_enable_cb.setChecked(False)
        self.qos_enable_cb.toggled.connect(self._on_qos_enable_toggled)

        exec_btn = QPushButton(i18n.t("btn_execute"))
        exec_btn.clicked.connect(self._on_execute)
        clear_btn = QPushButton(i18n.t("btn_clear"))
        clear_btn.clicked.connect(self._on_clear)

        size_row = QHBoxLayout()
        size_row.addWidget(self.size_edit)
        size_row.addWidget(self.unit_combo)

        qos_row = QHBoxLayout()
        qos_row.addWidget(self.qos_combo, 1)
        qos_row.addWidget(self.qos_enable_cb)

        form = QFormLayout()
        form.addRow(i18n.t("lbl_name"), self.name_edit)
        form.addRow(i18n.t("lbl_size"), size_row)
        form.addRow(i18n.t("lbl_aggregate"), self.aggregate_combo)
        form.addRow(i18n.t("lbl_qos"), qos_row)

        btn_row = QHBoxLayout()
        btn_row.addWidget(exec_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btn_row)
        layout.addStretch(1)

    def _update_qos_tooltip(self, text: str):
        self.qos_combo.setToolTip(self.qos_hints.get(text, ""))

    def _on_qos_enable_toggled(self, checked: bool):
        self.qos_combo.setEnabled(checked)
        if not checked:
            # Сняли блокировку - вернулись к безопасному дефолту «без QoS».
            no_qos_index = self.qos_combo.findText("no-qos")
            if no_qos_index >= 0:
                self.qos_combo.setCurrentIndex(no_qos_index)

    def _on_execute(self):
        name = self.name_edit.text().strip()
        ok, err_key = validate_name(name)
        if not ok:
            QMessageBox.warning(self, self.i18n.t("err_title"), self.i18n.t(err_key))
            return

        # Размер - целое положительное число (доки ONTAP: -size <integer>[KB|MB|GB|TB|PB]).
        ok_size, size = validate_size(self.size_edit.text())
        if not ok_size:
            QMessageBox.warning(self, self.i18n.t("err_title"), self.i18n.t(size))
            return

        command = build_volume_create(
            name=name,
            size_value=size,
            size_unit=self.unit_combo.currentText(),
            aggregate=self.aggregate_combo.currentText(),
            qos_policy=self.qos_combo.currentText(),
        )

        confirm = QMessageBox.question(
            self, self.i18n.t("confirm_title"), f"{self.i18n.t('confirm_text')}\n\n{command}"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.log(f"> {command}")
        try:
            result = self.session.backend.run_command(
                command, timeout=DEFAULT_TIMEOUT, expect=VOLUME_CREATE_OK_MARKER
            )
        except Exception as exc:
            self.log(f"[!] {exc}", level="error")
            QMessageBox.critical(self, self.i18n.t("err_title"), str(exc))
            return

        # Живой ответ СХД - как есть; факт успеха/ошибки дополнительно цветом.
        self.log(result.output)
        if result.success:
            self.log(
                f"{self.i18n.t('console_success')} ({result.matched})",
                level="success",
            )
        else:
            self.log(
                f"{self.i18n.t('console_error')}: "
                + self.i18n.t("console_timeout_marker").format(
                    marker=VOLUME_CREATE_OK_MARKER, timeout=int(DEFAULT_TIMEOUT)
                ),
                level="error",
            )

    def _on_clear(self):
        self.name_edit.clear()
        self.size_edit.clear()
        self.aggregate_combo.setCurrentIndex(0)
        # Сброс чекбокса возвращает комбо на no-qos и блокирует выбор.
        self.qos_enable_cb.setChecked(False)
