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
from ontap_commands import LUN_CREATE_OK_MARKER, build_lun_create
from settings import load_settings, save_settings
from validation import validate_name, validate_size


class LunTab(QWidget):
    def __init__(self, session, i18n, log_callback, volume_tab=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.log = log_callback
        self.volume_tab = volume_tab  # ссылка на VolumeTab для FR01 (повтор имени/размера)

        self.name_edit = QLineEdit()
        self.size_edit = QLineEdit()
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(list(SIZE_UNITS))

        # -ostype зависит от кластера (эталон C400.ps1: windows_gpt/linux, C800.ps1: windows/linux).
        self.ostype_combo = QComboBox()
        self.ostype_combo.addItems(list(session.cluster.lun_ostypes))

        # FR01: «Повторить имя и размер с вкладки Volume» - по умолчанию ОТМЕЧЕН
        # (у клиента в 99% случаев имя тома и LUN совпадают). При снятии чекбокса
        # вкладка LUN редактируется независимо. Состояние сохраняется в settings.json.
        self.repeat_cb = QCheckBox(i18n.t("lbl_repeat_vol_to_lun"))
        self.repeat_cb.setChecked(bool(load_settings().get("repeat_vol_to_lun", True)))
        self.repeat_cb.toggled.connect(self._on_repeat_toggled)

        exec_btn = QPushButton(i18n.t("btn_execute"))
        exec_btn.clicked.connect(self._on_execute)
        clear_btn = QPushButton(i18n.t("btn_clear"))
        clear_btn.clicked.connect(self._on_clear)

        size_row = QHBoxLayout()
        size_row.addWidget(self.size_edit)
        size_row.addWidget(self.unit_combo)

        form = QFormLayout()
        form.addRow(i18n.t("lbl_name"), self.name_edit)
        form.addRow(i18n.t("lbl_size"), size_row)
        form.addRow(i18n.t("lbl_ostype"), self.ostype_combo)
        form.addRow("", self.repeat_cb)

        btn_row = QHBoxLayout()
        btn_row.addWidget(exec_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btn_row)
        layout.addStretch(1)

    # --- FR01: перенос имени и размера с вкладки Volume ---

    def _on_repeat_toggled(self, checked: bool):
        # Сохраняем состояние чекбокса (как lang/theme - в settings.json).
        save_settings(repeat_vol_to_lun=checked)

    def _sync_from_volume(self):
        """Переносит имя и размер с вкладки Volume КАК ВВЕДЕНО (без квирка +3%).
        Квирк применяется фоном только при сборке команды volume create
        (уточнение оператора по FR01: на LUN уходит размер без квирка)."""
        if self.volume_tab is None:
            return
        self.name_edit.setText(self.volume_tab.name_edit.text().strip())
        self.size_edit.setText(self.volume_tab.size_edit.text().strip())
        vol_unit = self.volume_tab.unit_combo.currentText()
        idx = self.unit_combo.findText(vol_unit)
        if idx >= 0:
            self.unit_combo.setCurrentIndex(idx)

    def showEvent(self, event):
        # В момент переключения на вкладку LUN - если чекбокс отмечен, повторяем
        # имя и размер с Volume (значения могли поменяться).
        if self.repeat_cb.isChecked():
            self._sync_from_volume()
        super().showEvent(event)

    def _on_execute(self):
        # При создании LUN с отмеченным чекбоксом берём свежие значения с Volume
        # (перенос работает и при создании, а не только при переключении вкладок).
        if self.repeat_cb.isChecked():
            self._sync_from_volume()

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

        command = build_lun_create(
            name=name,
            size_value=size,
            size_unit=self.unit_combo.currentText(),
            ostype=self.ostype_combo.currentText(),
        )

        confirm = QMessageBox.question(
            self, self.i18n.t("confirm_title"), f"{self.i18n.t('confirm_text')}\n\n{command}"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.log(f"> {command}")
        try:
            result = self.session.backend.run_command(
                command, timeout=DEFAULT_TIMEOUT, expect=LUN_CREATE_OK_MARKER
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
                    marker=LUN_CREATE_OK_MARKER, timeout=int(DEFAULT_TIMEOUT)
                ),
                level="error",
            )

    def _on_clear(self):
        self.name_edit.clear()
        self.size_edit.clear()
        self.ostype_combo.setCurrentIndex(0)
