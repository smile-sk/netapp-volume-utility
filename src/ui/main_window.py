from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QTabWidget

from ui.console_widget import ConsoleWidget
from ui.tab_lun import LunTab
from ui.tab_mapping import MappingTab
from ui.tab_show import ShowTab
from ui.tab_volume import VolumeTab


class MainWindow(QMainWindow):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n

        target_label = i18n.t("target_prod") if session.target == "PROD" else i18n.t("target_test")
        self.setWindowTitle(
            f"{i18n.t('app_title')} - {session.cluster.display_name} - {target_label} ({session.host})"
        )
        self.resize(780, 660)

        self.console = ConsoleWidget(session, i18n)

        # Порядок важен: VolumeTab нужен LunTab (FR01), а MappingTab нужны оба
        # (автоподстановка имён Volume/LUN с предыдущих вкладок - заказ оператора).
        self.volume_tab = VolumeTab(session, i18n, self.console.log)
        self.lun_tab = LunTab(session, i18n, self.console.log, volume_tab=self.volume_tab)
        self.mapping_tab = MappingTab(
            session, i18n, self.console.log,
            volume_tab=self.volume_tab,
            lun_tab=self.lun_tab,
        )
        self.show_tab = ShowTab(session, i18n, self.console.log)

        tabs = QTabWidget()
        tabs.addTab(self.volume_tab, i18n.t("tab_volume"))
        tabs.addTab(self.lun_tab, i18n.t("tab_lun"))
        tabs.addTab(self.mapping_tab, i18n.t("tab_mapping"))
        tabs.addTab(self.show_tab, i18n.t("tab_show"))

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(tabs)
        splitter.addWidget(self.console)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

    def closeEvent(self, event):
        try:
            self.session.backend.disconnect()
        except Exception:
            pass
        super().closeEvent(event)
