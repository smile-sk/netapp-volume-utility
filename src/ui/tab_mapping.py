from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
)

from ontap_commands import build_igroup_show, build_lun_mapping_create, parse_igroup_names


class MappingTab(QWidget):
    """Примапить LUN.

    Порядок полей (по заказу оператора 2026-08-16): первым идёт Volume (логично -
    LUN живёт внутри тома), вторым LUN, затем igroup и LUN ID. Имена Volume/LUN
    автоматически подтягиваются с вкладок «Создать Volume» и «Создать LUN» при
    показе вкладки (showEvent).

    igroup - редактируемый комбо: список тянется с СХД командой
    `igroup show -vserver svm0 -fields igroup` (доки ONTAP 9.19.1) кнопкой
    «Обновить igroup» (и автоматически при первом показе вкладки, если комбо
    пусто), либо имя можно вписать руками - редактируемость комбо сохранена.
    """

    def __init__(self, session, i18n, log_callback, volume_tab=None, lun_tab=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.log = log_callback
        self.volume_tab = volume_tab  # ссылка на VolumeTab для автоподстановки имени
        self.lun_tab = lun_tab        # ссылка на LunTab для автоподстановки имени

        self.volume_edit = QLineEdit()
        self.lun_edit = QLineEdit()
        self.igroup_combo = QComboBox()
        self.igroup_combo.setEditable(True)  # можно выбрать из списка или вписать руками
        self.lun_id_edit = QLineEdit()

        exec_btn = QPushButton(i18n.t("btn_execute"))
        exec_btn.clicked.connect(self._on_execute)
        clear_btn = QPushButton(i18n.t("btn_clear"))
        clear_btn.clicked.connect(self._on_clear)
        refresh_btn = QPushButton(i18n.t("btn_refresh_igroup"))
        refresh_btn.clicked.connect(self._on_refresh_igroups)

        igroup_row = QHBoxLayout()
        igroup_row.addWidget(self.igroup_combo, 1)
        igroup_row.addWidget(refresh_btn)

        form = QFormLayout()
        # Порядок: Volume ПЕРВЫМ, LUN вторым (заказ оператора 2026-08-16).
        form.addRow(i18n.t("lbl_volume"), self.volume_edit)
        form.addRow(i18n.t("lbl_lun"), self.lun_edit)
        form.addRow(i18n.t("lbl_igroup"), igroup_row)
        form.addRow(i18n.t("lbl_lun_id"), self.lun_id_edit)
        self.form = form

        btn_row = QHBoxLayout()
        btn_row.addWidget(exec_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btn_row)
        layout.addStretch(1)

    # --- автоподстановка имён с вкладок Volume/LUN (заказ оператора) ---

    def _sync_from_tabs(self):
        """Подтягивает имена Volume/LUN с предыдущих вкладок (как введены)."""
        if self.volume_tab is not None:
            self.volume_edit.setText(self.volume_tab.name_edit.text().strip())
        if self.lun_tab is not None:
            self.lun_edit.setText(self.lun_tab.name_edit.text().strip())

    def showEvent(self, event):
        self._sync_from_tabs()
        # При первом показе (комбо ещё пусто) - тянем список igroup с СХД.
        if self.igroup_combo.count() == 0 and self.session.backend.connected:
            self._on_refresh_igroups()
        super().showEvent(event)

    # --- igroup: список с СХД + ручной ввод ---

    def _on_refresh_igroups(self):
        command = build_igroup_show()
        self.log(f"> {command}")
        try:
            result = self.session.backend.run_command(command)
        except Exception as exc:
            self.log(f"[!] {exc}", level="error")
            QMessageBox.critical(self, self.i18n.t("err_title"), str(exc))
            return
        self.log(result.output)
        names = parse_igroup_names(result.output)
        current = self.igroup_combo.currentText().strip()
        self.igroup_combo.clear()
        self.igroup_combo.addItems(names)
        if current:
            idx = self.igroup_combo.findText(current)
            if idx >= 0:
                self.igroup_combo.setCurrentIndex(idx)
            else:
                self.igroup_combo.setEditText(current)

    def _build_command(self) -> str:
        return build_lun_mapping_create(
            lun=self.lun_edit.text().strip(),
            volume=self.volume_edit.text().strip(),
            igroup=self.igroup_combo.currentText().strip(),
            lun_id=self.lun_id_edit.text().strip(),
        )

    def _on_execute(self):
        lun = self.lun_edit.text().strip()
        volume = self.volume_edit.text().strip()
        igroup = self.igroup_combo.currentText().strip()
        lun_id = self.lun_id_edit.text().strip()

        if not (lun and volume and igroup and lun_id):
            QMessageBox.warning(self, self.i18n.t("err_title"), self.i18n.t("err_fields_required"))
            return

        command = build_lun_mapping_create(lun=lun, volume=volume, igroup=igroup, lun_id=lun_id)

        confirm = QMessageBox.question(
            self, self.i18n.t("confirm_title"), f"{self.i18n.t('confirm_text')}\n\n{command}"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # Как в оригинале: mapping create не печатает маркер успеха - без фильтра,
        # вывод показывается как есть (успех проверяется во вкладке «Показать»).
        self.log(f"> {command}")
        try:
            result = self.session.backend.run_command(command)
            self.log(result.output)
        except Exception as exc:
            self.log(f"[!] {exc}", level="error")
            QMessageBox.critical(self, self.i18n.t("err_title"), str(exc))

    def _on_clear(self):
        self.volume_edit.clear()
        self.lun_edit.clear()
        self.igroup_combo.setEditText("")
        self.lun_id_edit.clear()
