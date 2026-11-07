import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.main_window import MDPayer
from services.core import init_db


os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "ffmpeg"
if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    ex = MDPayer()
    ex.show()
    sys.exit(app.exec())