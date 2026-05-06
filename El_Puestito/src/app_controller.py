import os
import json
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from logger_setup import setup_logger
from printer_service import PrinterService

logger = setup_logger()

class AppController(QObject):
    
    lista_empleados_actualizada = pyqtSignal()
    ordenes_actualizadas = pyqtSignal()
    asistencia_recibida = pyqtSignal(dict)
    error_ocurrido = pyqtSignal(str)

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.network_manager = QNetworkAccessManager()
        self.config = self._load_config()
        self.API_KEY = self.config.get("api_key", "puestito_seguro_2025")
        self.SERVER_URL = self.config.get("server_url", "http://127.0.0.1:5000")
        self.printer_service = PrinterService(self)
        logger.info(f"[AppController] Inicializado con API Key cargada y URL: {self.SERVER_URL}")

    def get_config(self):
        return self.config

    def _load_config(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "assets", "config.json")
            
            if not os.path.exists(config_path):
                logger.warning(f"No se encontro {config_path}")
                return {}
                
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando configuracion en Controller: {e}")
            return {}

    def get_todos_los_empleados(self):
        return self.data_manager.get_employees()

    def agregar_empleado(self, new_id, new_name, new_rol, fingerprint_id=None):
        result = self.data_manager.add_employee(new_id, new_name, new_rol, fingerprint_id)
        if result: self.lista_empleados_actualizada.emit()
        return result

    def editar_empleado(self, original_id, new_id, new_name, new_rol, fingerprint_id=None):
        result = self.data_manager.update_employee(original_id, new_id, new_name, new_rol, fingerprint_id)
        if result: self.lista_empleados_actualizada.emit()
        return result

    def eliminar_empleado(self, employee_id):
        result = self.data_manager.delete_employee(employee_id)
        if result: self.lista_empleados_actualizada.emit()
        return result
    
    def save_config_to_file(self, config_data):
        import json
        import os
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "assets", "config.json")
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            self.config = config_data
            logger.info("Configuracion guardada en config.json")
        except Exception as e:
            logger.critical(f"Error guardando config.json: {e}")

    def notificar_evento_servidor(self, nombre_evento):
        url = QUrl(f'{self.SERVER_URL}/trigger_update')
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setRawHeader(b"X-API-KEY", self.API_KEY.encode('utf-8'))
        
        payload = json.dumps({'event': nombre_evento}).encode('utf-8')
        
        reply = self.network_manager.post(request, payload)
        reply.finished.connect(lambda: self._handle_reply(reply))
    
    def procesar_nueva_orden(self, orden_completa):
        logger.info("[Controller] Procesando nueva orden...")
        try:
            nuevo_id = self.data_manager.create_new_order(orden_completa)
            if nuevo_id is None: 
                raise Exception("Fallo en base de datos al crear orden")

            self.ordenes_actualizadas.emit() 
            self.notificar_cambios_mesas()

        except Exception as e:
            logger.error(f"Error CRITICO al guardar orden: {e}")
            self.error_ocurrido.emit(f"No se guardo la orden:\n{e}")

    def cobrar_cuenta(self, mesa_key, order_data=None):
        logger.info(f"[Controller] Cobrando mesa {mesa_key}...")
        try:
            orden_cerrada = self.data_manager.complete_order(mesa_key)
            if orden_cerrada:
                logger.info(f"Mesa {mesa_key} cerrada en BD.")
                self.printer_service.open_cash_drawer()
                if order_data:
                    self.printer_service.print_receipt(order_data)
                
                self.ordenes_actualizadas.emit()
                self.notificar_cambios_mesas()
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error al cobrar cuenta: {e}")
            return False

    def registrar_impresion_proforma(self, mesa_key):
        return self.data_manager.registrar_impresion_proforma(mesa_key)

    def notificar_cambios_mesas(self):
        self.notificar_evento_servidor("mesas_update")
        
    def formatear_sensor_biometrico(self):
        url = QUrl(f'{self.SERVER_URL}/api/biometric/start-clear')
        request = QNetworkRequest(url)
        request.setRawHeader(b"X-API-KEY", self.API_KEY.encode('utf-8'))
        
        reply = self.network_manager.post(request, b"")
        reply.finished.connect(lambda: self._handle_reply(reply))

    def _handle_reply(self, reply):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            logger.error(f"Error notificando al servidor: {reply.errorString()}")
        reply.deleteLater()