import os
import re
from i18n import _
from service.flatpak_service import FlatpakService
from ui.pkg_manager import PkgManager, PKGAction


class FlatpakManager(PkgManager):
    def __init__(self, target_url: str, action: PKGAction | None = None):
        super().__init__(title=_("Flatpak Manager"), action=action)

        self.service = FlatpakService(self.process)
        self.target_url = target_url
        self.target_base_name = os.path.basename(self.target_url)
        self.target_name = self.service.extract_name(self.target_base_name)

        self.intialize_application()

    def intialize_application(self):
        if self.service.is_installed(self.target_base_name) or self.pkg_action == PKGAction.REMOVE:
            self.current_progress.setRange(0, 0) 
            self.start_removal(self.target_name, self.target_base_name)
        else:
            self.start_installation(self.target_name, self.target_url)


    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        match = re.search(r'(\d+)%', data)
        if match:
            self.current_progress.setValue(int(match.group(1)))
