from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import QMessageBox
import json

class AppController(QObject):
    
    lista_empleados_actualizada = pyqtSignal()
    ordenes_actualizadas = pyqtSignal()
    
    API_KEY = "puestito_seguro_2025" 

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.network_manager = QNetworkAccessManager()

    def get_todos_los_empleados(self):
        return self.data_manager.get_employees()

    def agregar_empleado(self, new_id, new_name, new_rol):
        result = self.data_manager.add_employee(new_id, new_name, new_rol)
        if result: self.lista_empleados_actualizada.emit()
        return result

    def editar_empleado(self, original_id, new_id, new_name, new_rol):
        result = self.data_manager.update_employee(original_id, new_id, new_name, new_rol)
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
            self._notificar_servidor_mesas_actualizadas()

        except Exception as e:
            print(f"Error CRÍTICO: {e}")
            QMessageBox.critical(None, "Error", f"No se guardó la orden:\n{e}")

    def cobrar_cuenta(self, mesa_key):

        print(f"[Controller] Cobrando mesa {mesa_key}...")
        try:
            orden_cerrada = self.data_manager.complete_order(mesa_key)
            
            if orden_cerrada:
                print(f"✅ Mesa {mesa_key} cerrada en BD.")
                self._notificar_servidor_mesas_actualizadas()
                return True
            else:
                print(f"⚠️ No se pudo cerrar la orden de la mesa {mesa_key} (¿Ya estaba cerrada?)")
                return False

        except Exception as e:
            print(f"Error al cobrar: {e}")
            return False

    def _notificar_servidor_mesas_actualizadas(self):
        """Envía la señal al servidor Flask con la LLAVE DE SEGURIDAD."""
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
        else:
            print(f"Notificación enviada con éxito (Status {reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)})")
        reply.deleteLater()