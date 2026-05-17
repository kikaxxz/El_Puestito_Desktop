import sys
import traceback

try:
    from PyQt6.QtWidgets import QApplication
    from path_manager import get_asset_path
    from PyQt6.QtGui import QIcon
    from main_window import MainWindow

    if __name__ == "__main__":
        app = QApplication(sys.argv)
        icono_path = get_asset_path("logo.ico") 
        app.setWindowIcon(QIcon(icono_path))
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
        
except Exception:
    with open("ERROR_CRITICO.txt", "w") as f:
        traceback.print_exc(file=f)