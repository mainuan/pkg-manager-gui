import os
import re
from PySide6.QtWidgets import QMessageBox
from i18n import _
from service.appimage_service import AppImageService
from ui.pkg_manager import PkgManager, PKGAction

# Código de saída do appimage_manager_backend para um arquivo que não é um
# AppImage tipo 2 (o backend não executa o AppImage para extraí-lo).
EXIT_UNSUPPORTED = 3


class AppImageManager(PkgManager):
    def __init__(self, target_url: str, action: PKGAction | None = None):
        super().__init__(title=_("AppImage Manager"), action=action)

        self.service = AppImageService(self.process)
        self.target_url = target_url
        self.target_base_name = os.path.basename(self.target_url)
        self.target_name = self.service.extract_name(self.target_base_name)

        self.intialize_application()

    def intialize_application(self): 
        self.current_progress.setRange(0, 0) 
        if self.service.is_installed(self.target_base_name) or self.pkg_action == PKGAction.REMOVE:
            self.start_removal(self.target_name, self.target_base_name)
        else:
            self.start_installation(self.target_name, self.target_url)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        match = re.search(r'(\d+)%', data)
        if match:
            self.current_progress.setValue(int(match.group(1)))

    def on_finished(self, exit_code):
        if exit_code == EXIT_UNSUPPORTED:
            QMessageBox.warning(
                self, _("Warning"),
                _("This file is not a supported AppImage. Only type 2 AppImages can be "
                  "installed; type 1 AppImages and other files are refused."))
            self.close()
            return
        super().on_finished(exit_code)
