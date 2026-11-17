import sys
from PySide6.QtWidgets import (QApplication)
from factory.ui_factory import BuildUi
from i18n import _, install_qt_translator

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qt_translator = install_qt_translator(app)
    if len(sys.argv) < 2:
        # Translators: placeholder for the command-line argument in the usage line.
        argument = _("url/file")
        print(_("Usage: {command}").format(command=f"pkg-manager-gui <{argument}>"))
        sys.exit(1)

    window = BuildUi.AutoInferPkg(sys.argv[1])
    window.show()
    sys.exit(app.exec())
