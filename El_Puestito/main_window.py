import sys
import os
import json
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QMessageBox
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
try:
    from data_model import DataManager, DB_PATH
except ImportError:
    sys.exit(1)

from path_manager import get_persistent_path, get_asset_path
from server.server_worker import ServerWorker
from server.server_thread import ServerThread
from views.attendance_page import AttendancePage
from views.cocina_page import CocinaPage
from views.barra_page import BarraPage
from views.caja_page import CajaPage
from views.role_selection_page import RoleSelectionPage
from views.admin_page import AdminPage
from widgets.qr_code_dialog import QRCodeDialog
from src.app_controller import AppController
from logger_setup import setup_logger

logger = setup_logger()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class MainWindow(QMainWindow):

    trigger_server_stop = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.load_app_config()
        
        self.data_manager = DataManager(DB_PATH)
        self.data_manager.create_tables()
        self.data_manager.run_migration_if_needed()
        self.app_controller = AppController(self.data_manager)

        self.setWindowTitle("El Puestito - Sistema de Gestión")
        self.setMinimumSize(1200, 800)
        self.current_role = None
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.sidebar = self.create_sidebar()
        self.stacked_widget = QStackedWidget()

        logger.info("Creando páginas de la interfaz...")
        self.page_attendance = AttendancePage(self.app_controller)
        self.page_role_selection = RoleSelectionPage() 
        self.page_cocina = CocinaPage(self.app_controller, self)
        self.page_caja = CajaPage(self.app_controller)
        self.page_barra = BarraPage(self.app_controller, self) 
        self.page_admin = AdminPage(self.app_controller, self.app_config)

        self.role_pages_map = {
            "Cocinero": self.page_cocina,
            "Cajero": self.page_caja,
            "Barra": self.page_barra,
            "Administrador": self.page_admin
        }

        self.stacked_widget.addWidget(self.page_attendance)
        self.stacked_widget.addWidget(self.page_role_selection)
        self.stacked_widget.addWidget(self.page_cocina)
        self.stacked_widget.addWidget(self.page_caja)
        self.stacked_widget.addWidget(self.page_barra)
        self.stacked_widget.addWidget(self.page_admin)

        self.app_controller.ordenes_actualizadas.connect(self.page_caja.load_active_orders)
        self.app_controller.ordenes_actualizadas.connect(self.page_cocina.load_active_orders)
        self.app_controller.ordenes_actualizadas.connect(self.page_barra.load_active_orders)
        self.app_controller.lista_empleados_actualizada.connect(self.page_attendance.load_and_refresh_table)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stacked_widget)
        
        self.btn_qr.clicked.connect(self.show_qr_dialog)
        self.page_role_selection.role_selected.connect(self.handle_role_selection)
        
        self.page_admin.config_updated.connect(self.update_and_save_config)
        
        self.load_stylesheet("style.qss")

        logger.info("Creando ServerWorker en Hilo Principal...")
        self.server_worker = ServerWorker(self.data_manager) 

        logger.info("Creando ServerThread...")
        self.thread = ServerThread(worker_instance=self.server_worker)
        
        self.server_worker.nueva_orden_recibida.connect(self.app_controller.procesar_nueva_orden)
        self.server_worker.ordenes_modificadas.connect(self.app_controller.ordenes_actualizadas.emit)
        self.server_worker.kds_estado_cambiado.connect(self.on_kds_externo_update)
        self.server_worker.asistencia_recibida.connect(self.app_controller.asistencia_recibida.emit)

        self.thread.start()
        logger.info("Servidor de asistencia iniciado en segundo plano.")

    def update_and_save_config(self, updated_config):
        self.app_config = updated_config 
        self.save_app_config() 

    def load_app_config(self):
        self.config_file_path = get_persistent_path("config.json")
        default_config = {
            "total_mesas": 10,
            "seguridad": {
                "pines": {
                    "Cajero": "3333",
                    "Administrador": "9999",
                    "Cocinero": "1111",
                    "Barra": "2222"
                }
            },
            "roles_pago": {
                "Mesero": {"minuto": 0.5},
                "Cajera": {"minuto": 0.6},
                "Jefe de Cocina": {"minuto": 0.8},
                "Michelero": {"minuto": 0.5}
            }
        }

        try:
            with open(self.config_file_path, "r") as f:
                loaded_config = json.load(f)
                self.app_config = {**default_config, **loaded_config}
            logger.info(f"Configuración cargada desde {self.config_file_path}")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("No se encontró config.json o está corrupto. Usando config por defecto.")
            self.app_config = default_config 

    def save_app_config(self):
        try:
            with open(self.config_file_path, "w") as f:
                json.dump(self.app_config, f, indent=4)
            logger.info(f"Configuración guardada en {self.config_file_path}")
        except IOError:
            logger.error("Error al guardar la configuración.")
        
    def show_qr_dialog(self):
        dialog = QRCodeDialog(self)
        dialog.exec()

    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        logo_label = QLabel()
        logo_path = get_asset_path("Logo.png")

        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaledToWidth(150, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_attendance = QPushButton("Control de Asistencia")
        self.btn_attendance.setObjectName("nav_button")
        self.btn_attendance.setProperty("active", True)
        
        self.btn_pos = QPushButton("Punto de Venta")
        self.btn_pos.setObjectName("nav_button")
        
        self.btn_attendance.clicked.connect(lambda: self.switch_page(0))
        self.btn_pos.clicked.connect(lambda: self.switch_page(1))
        
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(30)
        sidebar_layout.addWidget(self.btn_attendance)
        sidebar_layout.addWidget(self.btn_pos)
        sidebar_layout.addStretch() 
        
        self.btn_qr = QPushButton("Conexión QR")
        self.btn_qr.setObjectName("nav_button") 
        sidebar_layout.addWidget(self.btn_qr)
        
        return sidebar
    
    def switch_page(self, index):
        self.btn_attendance.setProperty("active", index == 0)
        self.btn_pos.setProperty("active", index == 1)
        self.btn_attendance.style().polish(self.btn_attendance)
        self.btn_pos.style().polish(self.btn_pos)
        
        if index == 0:
            self.stacked_widget.setCurrentWidget(self.page_attendance)
        elif index == 1:
            self.current_role = None 
            self.page_role_selection.reset_state()
            self.stacked_widget.setCurrentWidget(self.page_role_selection)
        
    def handle_role_selection(self, role_name):
        self.current_role = role_name
        target_page = self.role_pages_map.get(role_name)
        
        if target_page:
            self.stacked_widget.setCurrentWidget(target_page)
        else:
            logger.warning(f"No hay una vista definida para el rol: {role_name}")
    
    def load_stylesheet(self, filename):
        try:
            absolute_path = get_asset_path(filename)
            logger.info(f"Intentando cargar la hoja de estilos desde: {absolute_path}")

            with open(absolute_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
                
        except FileNotFoundError:
            logger.warning(f"No se encontró el archivo de estilos '{filename}' en la ruta calculada.")

    def closeEvent(self, event):
        logger.info("Cerrando la aplicación...")

        if hasattr(self, 'thread') and self.thread.isRunning():
            logger.info("Deteniendo el hilo del servidor...")
            self.server_worker.stop_server() 
            
            logger.info("Esperando finalización del hilo...")
            if not self.thread.wait(3000): 
                logger.warning("El hilo del servidor tardó demasiado en cerrarse, forzando terminación.")
                self.thread.terminate() 
            else:
                logger.info("Hilo del servidor detenido limpiamente.")
        
        self.save_app_config() 
        super().closeEvent(event)

    def on_kds_externo_update(self, destino):
        logger.info(f"Actualizando vista de escritorio por cambio en Web ({destino})")
        
        if destino in ['cocina', 'all']:
            if hasattr(self, 'page_cocina'):
                self.page_cocina.load_active_orders() 

        if destino in ['barra', 'all']:
            if hasattr(self, 'page_barra'):
                self.page_barra.load_active_orders()