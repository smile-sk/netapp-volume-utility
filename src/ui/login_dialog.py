"""Логин при старте. Учётные данные живут только в локальных переменных этой
функции и в открытом SSH-соединении backend'а - на диск ничего не пишется.
На диск пишутся только безобидные предпочтения (язык, тема) - см. settings.py.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from app_config import CLUSTERS, SSH_PORT, TARGETS
from assets_data import login_logo_png
from backend.fake import FakeBackend
from backend.real import RealBackend
from i18n import LANG_NAMES
from session import Session
from settings import load_settings, save_settings
from theme import THEME_KEYS, apply_theme

# Порядок строк формы: (ключ i18n для метки, имя атрибута-виджета).
# Тестовая версия: выбор цели (PROD/TEST) и режима (Real/Fake) доступен.
_FORM_ROWS = (
    ("login_lang", "lang_combo"),
    ("login_theme", "theme_combo"),
    ("login_user", "user_edit"),
    ("login_pass", "pass_edit"),
    ("login_cluster", "cluster_combo"),
    ("login_target", "target_combo"),
    ("login_host", "host_edit"),
    ("login_backend", "backend_combo"),
)


class LoginDialog(QDialog):
    def __init__(self, i18n, initial_theme: str = "light", parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.session: Session | None = None
        self.theme = initial_theme if initial_theme in THEME_KEYS else "light"

        self.setWindowTitle(i18n.t("login_title"))
        self.setModal(True)

        self.lang_combo = QComboBox()
        for code, label in LANG_NAMES.items():
            self.lang_combo.addItem(label, userData=code)
        self.lang_combo.setCurrentIndex(list(LANG_NAMES.keys()).index(i18n.lang))
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)

        self.theme_combo = QComboBox()
        self._fill_theme_combo()
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self.cluster_combo = QComboBox()
        self.cluster_combo.addItems(list(CLUSTERS.keys()))

        self.target_combo = QComboBox()
        self.target_combo.addItems(list(TARGETS))

        self.backend_combo = QComboBox()
        self.backend_combo.addItem(i18n.t("login_backend_real"), userData="real")
        self.backend_combo.addItem(i18n.t("login_backend_fake"), userData="fake")

        self.host_edit = QLineEdit()
        self._prefs = load_settings()
        self._update_host_field()
        self.cluster_combo.currentIndexChanged.connect(lambda *_: self._update_host_field())
        self.target_combo.currentIndexChanged.connect(lambda *_: self._update_host_field())

        # Метки формы хранятся отдельно: при смене языка обновляются их тексты,
        # а не пересобирается вся форма. ВАЖНО: QFormLayout.removeRow удаляет
        # виджеты строки (layout владеет ими) - переиспользование старой ссылки
        # даёт RuntimeError shiboken «Internal C++ object already deleted».
        self._labels: dict[str, QLabel] = {
            key: QLabel(i18n.t(key)) for key, _ in _FORM_ROWS
        }
        self.form = QFormLayout()
        for key, attr in _FORM_ROWS:
            self.form.addRow(self._labels[key], getattr(self, attr))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        self.buttons = buttons

        layout = QVBoxLayout(self)
        layout.addLayout(self.form)

        # Логотип: между последней строкой формы и кнопками, пропорционально.
        # Картинка вшита в exe (assets_data) - работает автономно; файл с диска
        # используется как запасной вариант (запуск из исходников).
        self.logo_label = QLabel()
        logo_pix = QPixmap()
        logo_pix.loadFromData(login_logo_png)
        if logo_pix.isNull():
            logo_path = Path(__file__).resolve().parent.parent / "assets" / "login_logo.png"
            logo_pix = QPixmap(str(logo_path))
        if not logo_pix.isNull():
            # Нативный размер 1:1 с файлом: физический размер пиксмапа = размеру
            # PNG, независимо от масштабирования Windows (DPR > 1). Без этого
            # на экране 125% картинка выглядит на 25% больше оригинала.
            app = QApplication.instance()
            if app is not None:
                logo_pix.setDevicePixelRatio(app.devicePixelRatio())
            self.logo_label.setPixmap(logo_pix)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.logo_label)
        layout.addWidget(buttons)

        # Сохранённая тема видна уже на окне входа (живое превью с первого кадра).
        self._apply_theme()

    def _fill_theme_combo(self):
        """Заполняет комбо тем; подписи зависят от языка, поэтому пересобирается."""
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        for code in THEME_KEYS:
            self.theme_combo.addItem(self.i18n.t(f"theme_{code}"), userData=code)
        idx = self.theme_combo.findData(self.theme)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.theme_combo.blockSignals(False)

    def _apply_theme(self):
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, self.theme)

    def _retranslate(self):
        """Обновляет все тексты при смене языка - без пересборки виджетов."""
        i18n = self.i18n
        self.setWindowTitle(i18n.t("login_title"))
        for key, label in self._labels.items():
            label.setText(i18n.t(key))
        self._fill_theme_combo()
        self.backend_combo.setItemText(0, i18n.t("login_backend_real"))
        self.backend_combo.setItemText(1, i18n.t("login_backend_fake"))

    def _on_lang_changed(self, index: int):
        self.i18n.set_lang(self.lang_combo.itemData(index))
        self._retranslate()

    def _on_theme_changed(self, index: int):
        self.theme = self.theme_combo.itemData(index)
        self._apply_theme()

    def _update_host_field(self):
        """Подставляет адрес для текущего кластера/цели:
        сначала сохранённый в settings.json
        (переопределение), иначе дефолт из app_config."""
        cluster_key = self.cluster_combo.currentText()
        target = self.target_combo.currentText() or "PROD"
        saved = self._prefs.get("hosts", {}).get(cluster_key, {}).get(target)
        self.host_edit.setText(saved or CLUSTERS[cluster_key].hosts.get(target, ""))

    def _on_accept(self):
        cluster_key = self.cluster_combo.currentText()
        cluster = CLUSTERS[cluster_key]
        target = self.target_combo.currentText() or "PROD"
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()

        host = self.host_edit.text().strip()
        if not host:
            QMessageBox.critical(self, self.i18n.t("err_title"), self.i18n.t("err_host_required"))
            return

        # Тестовая версия: режим выбирается на окне входа.
        backend_key = self.backend_combo.currentData() or "real"
        if backend_key == "fake":
            backend = FakeBackend()
        else:
            backend = RealBackend()

        try:
            backend.connect(host, SSH_PORT, username, password)
        except Exception as exc:
            QMessageBox.critical(self, self.i18n.t("err_title"), f"{self.i18n.t('err_connect')}: {exc}")
            return

        self.session = Session(
            cluster=cluster,
            target=target,
            username=username,
            backend=backend,
            host=host,
            theme=self.theme,
        )
        # Запоминаем последний выбор языка, темы (не креды!)
        # и переопределение адреса для этого кластера/цели.
        hosts = dict(self._prefs.get("hosts", {}))
        hosts[cluster_key] = {**hosts.get(cluster_key, {}), target: host}
        save_settings(self.i18n.lang, self.theme, hosts=hosts)
        self.accept()
