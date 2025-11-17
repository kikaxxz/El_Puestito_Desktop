from PyQt6.QtCore import QObject, pyqtSignal
import requests
from PyQt6.QtWidgets import QMessageBox

class AppController(QObject):
    """
    Controlador central que maneja la lógica de negocio
    y actúa como intermediario entre el modelo de datos y las vistas.
    """
    
    lista_empleados_actualizada = pyqtSignal()
    ordenes_actualizadas = pyqtSignal()

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager


    def get_todos_los_empleados(self):
        """Pasa la solicitud para obtener todos los empleados."""
        return self.data_manager.get_employees()

    def agregar_empleado(self, new_id, new_name, new_rol):
        """
        Agrega un empleado y, si tiene éxito,
        emite una señal para notificar a todas las vistas.
        """
        print(f"[Controller] Intentando agregar empleado: {new_id}")
        
        result = self.data_manager.add_employee(new_id, new_name, new_rol)
        
        if result:
            print(f"[Controller] Empleado agregado. Emitiendo señal 'lista_empleados_actualizada'.")
            self.lista_empleados_actualizada.emit()
            
        return result

    def editar_empleado(self, original_id, new_id, new_name, new_rol):
        """
        Edita un empleado y, si tiene éxito, emite la señal.
        """
        print(f"[Controller] Intentando editar empleado: {original_id}")
        result = self.data_manager.update_employee(original_id, new_id, new_name, new_rol)
        if result:
            print(f"[Controller] Empleado editado. Emitiendo señal 'lista_empleados_actualizada'.")
            self.lista_empleados_actualizada.emit()
            
        return result

    def eliminar_empleado(self, employee_id):
        """
        Elimina un empleado y, si tiene éxito, emite la señal.
        """
        print(f"[Controller] Intentando eliminar empleado: {employee_id}")
        result = self.data_manager.delete_employee(employee_id)
        if result:
            print(f"[Controller] Empleado eliminado. Emitiendo señal 'lista_empleados_actualizada'.")
            self.lista_empleados_actualizada.emit()
            
        return result
    
    def procesar_nueva_orden(self, orden_completa):
        """
        Guarda una nueva orden en la BD y notifica a las vistas.
        """
        print("[Controller] Procesando nueva orden...")
        try:
            # 1. Llama al DataManager para guardar
            nuevo_id_orden = self.data_manager.create_new_order(orden_completa)
            if nuevo_id_orden is None:
                raise Exception("create_new_order falló y no devolvió ID.")

            print(f"[Controller]  -> Orden {nuevo_id_orden} guardada en la BD.")

            self.ordenes_actualizadas.emit()
            print("[Controller]  -> Emitiendo señal 'ordenes_actualizadas'.")

            try:
                requests.post('http://127.0.0.1:5000/trigger_update', json={'event': 'mesas_actualizadas'})
                print("[Controller]  -> Notificación 'mesas_actualizadas' enviada a las apps móviles.")
            except requests.exceptions.RequestException as e:
                print(f"⚠️ [Controller] No se pudo notificar a los clientes (trigger_update): {e}")

        except Exception as e:
            print(f"❌❌ CRÍTICO: Error al guardar orden en la BD: {e}")
            QMessageBox.critical(self, "Error Crítico", f"No se pudo guardar la orden en la base de datos:\n{e}")  