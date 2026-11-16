from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget,
                               QLabel, QProgressBar, QPushButton, QMessageBox)
from PySide6.QtCore import QProcess, Qt
from enum import Enum
import sys
from service.pkg_service import PkgService
from i18n import _


class PKGAction(Enum):
    INSTALL = 0
    REMOVE = 1
    INSTALL_MULTI_PKG = 2
    AUTO = 3


class PkgManager(QMainWindow):
    def __init__(self, title: str, service: PkgService | None = None, action: PKGAction = None, other_progress_bar: QProgressBar | None = None):
        if action == None:
            action = PKGAction.AUTO

        super().__init__()
        self.setWindowTitle(title)
        self.setFixedSize(500, 250)
        self.pkg_action = action
        self.service = service

        # UI Setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)

        self.label = QLabel(_("<b>Checking status...</b>"))
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)

        self.current_progress = QProgressBar()
        self.current_progress.setFormat(
            # Translators: progress bar text; %p is replaced by Qt with the percentage.
            _("Current action: %p%"))
        self.layout.addWidget(self.current_progress)

        if isinstance(other_progress_bar, QProgressBar):
            self.layout.addWidget(other_progress_bar)

        self.btn_cancel = QPushButton(_("Cancel"))
        self.btn_cancel.clicked.connect(self.close)
        self.layout.addWidget(self.btn_cancel)

        # Processo e Serviço
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.finished.connect(self.on_finished)

    def intialize_application(self):
        raise NotImplementedError(
            "Você precisa implementar este método nas subclasses!")

    def handle_stdout(self):
        raise NotImplementedError(
            "Você precisa implementar este método nas subclasses!")

    def on_finished(self, exit_code):
        if exit_code == 0:
            QMessageBox.information(
                self, _("Success"), _("Operation completed successfully!"))
        else:
            QMessageBox.warning(
                self, _("Warning"), _("The operation was interrupted or finished with errors."))
        self.close()

    def start_installation(self, target_name: str, target_ref: str):
        if self.pkg_action == PKGAction.AUTO and not self.msg_box_install(target_name):
            sys.exit(0)

        self.label.setText(
            _("<b>Installing:</b> {name}").format(name=target_name) + " 😎")
        try:
            self.service.install(target_ref)
        except Exception as e:
            QMessageBox.critical(self, _("Error"),
                                 _("Installation failed: {error}").format(error=e))
            sys.exit(1)

    def start_removal(self, target_name: str, target_ref: str):
        if self.pkg_action == PKGAction.AUTO and not self.msg_box_remove(self.target_name):
            sys.exit(0)

        self.label.setText(
            _("<b>Removing:</b> {name}").format(name=target_name) + " 😥")
        try:
            self.service.uninstall(target_ref)
        except Exception as e:
            QMessageBox.critical(self, _("Error"),
                                 _("Removal failed: {error}").format(error=e))
            sys.exit(1)

    def msg_box_remove(self, package_name: str):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(_("Application Already Installed"))
        msg_box.setText(
            _("The package '{name}' is already installed on the system.").format(name=package_name))
        msg_box.setInformativeText(_("Do you want to remove it?"))
        btn_sim = msg_box.addButton(
            _("Uninstall"), QMessageBox.YesRole)
        btn_no = msg_box.addButton(_("Cancel"), QMessageBox.NoRole)
        
        btn_no.setFocus()
        msg_box.exec()

        return msg_box.clickedButton() == btn_sim

    def msg_box_install(self, package_name: str):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(_("Confirm Installation"))
        msg_box.setText(
            _("The package '{name}' is not installed on the system.").format(name=package_name))
        msg_box.setInformativeText(_("Do you want to install it?"))
        btn_sim = msg_box.addButton(
            _("Install"), QMessageBox.YesRole)
        msg_box.addButton(_("Cancel"), QMessageBox.NoRole)
        msg_box.exec()

        return msg_box.clickedButton() == btn_sim
