import os
import json
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import QMessageBox

class AppController(QObject):
    
    lista_empleados_actualizada = pyqtSignal()
    ordenes_actualizadas = pyqtSignal()
    asistencia_recibida = pyqtSignal(dict)

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.network_manager = QNetworkAccessManager()
        self.config = self._load_config()
        self.API_KEY = self.config.get("api_key", "puestito_seguro_2025") 
        print(f"[AppController] API Key cargada: {self.API_KEY}")

    def _load_config(self):
        """Carga config.json desde la carpeta assets."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "assets", "config.json")
            
            if not os.path.exists(config_path):
                print(f"⚠️ Alerta: No se encontró {config_path}")
                return {}
                
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando configuración en Controller: {e}")
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
    
    def procesar_nueva_orden(self, orden_completa):
        print("[Controller] Procesando nueva orden...")
        try:
            nuevo_id = self.data_manager.create_new_order(orden_completa)
            if nuevo_id is None: raise Exception("Fallo BD al crear orden")

            self.ordenes_actualizadas.emit() 
            self.notificar_cambios_mesas()

        except Exception as e:
            print(f"Error CRÍTICO: {e}")
            QMessageBox.critical(None, "Error", f"No se guardó la orden:\n{e}")

    def cobrar_cuenta(self, mesa_key):
        print(f"[Controller] Cobrando mesa {mesa_key}...")
        try:
            orden_cerrada = self.data_manager.complete_order(mesa_key)
            if orden_cerrada:
                print(f"Mesa {mesa_key} cerrada en BD.")
                self.ordenes_actualizadas.emit()
                self.notificar_cambios_mesas()
                return True
            else:
                return False
        except Exception as e:
            print(f"Error al cobrar: {e}")
            return False

    def notificar_cambios_mesas(self):
        """Envía la señal al servidor Flask usando la API KEY cargada."""
        url = QUrl('http://127.0.0.1:5000/trigger_update')
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        request.setRawHeader(b"X-API-KEY", self.API_KEY.encode('utf-8'))
        
        payload = json.dumps({'event': 'mesas_actualizadas'}).encode('utf-8')
        
        reply = self.network_manager.post(request, payload)
        reply.finished.connect(lambda: self._handle_reply(reply))

    def _handle_reply(self, reply):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            print(f"Error notificando al servidor: {reply.errorString()}")
        reply.deleteLater()