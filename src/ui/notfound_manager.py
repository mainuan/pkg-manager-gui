from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget,
                               QLabel, QPushButton)
from PySide6.QtCore import Qt
from i18n import _


class NotFoundManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("System Notice"))
        self.setFixedSize(350, 280)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QLabel {
                font-family: 'Segoe UI', sans-serif;
                color: #333333;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        central_widget.setLayout(layout)

        lbl_icon = QLabel("⚠️")
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet(
            "font-size: 60px; color: #ffcc00; margin-bottom: 10px;")
        layout.addWidget(lbl_icon)

        lbl_title = QLabel(_("Unsupported Format"))
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #222;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            _("The detected package format is not supported by this version."))
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(
            "font-size: 13px; color: #666; margin-bottom: 10px;")
        layout.addWidget(lbl_desc)

        layout.addStretch()

        btn_close = QPushButton(_("Got it, close"))
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)
