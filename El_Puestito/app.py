import sys
import os
import traceback
import ctypes
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def check_firewall_rule():
    comando = 'netsh advfirewall firewall show rule name="El Puestito Server"'
    resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
    return "El Puestito Server" in resultado.stdout

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def setup_firewall():
    if check_firewall_rule():
        return

    if is_admin():
        comando = 'netsh advfirewall firewall add rule name="El Puestito Server" dir=in action=allow protocol=TCP localport=5000 profile=any'
        subprocess.run(comando, shell=True, capture_output=True)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

try:
    setup_firewall()
    
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