import os
import json
from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QThreadPool
from logger_setup import setup_logger
from src.services.printer_service import PrinterService
from path_manager import get_persistent_path
from src.services.notification_service import notification_service
from background_tasks import Worker

logger = setup_logger()

class LegacyDataManager:
    def __init__(self, ac):
        from src.database.connection import db_manager
        from src.database.repositories.menu import menu_repo
        from src.database.repositories.attendance import attendance_repo
        self.ac = ac
        self.db = db_manager
        self.menu = menu_repo
        self.attendance = attendance_repo
    def __getattr__(self, name):
        if hasattr(self.db, name): return getattr(self.db, name)
        if hasattr(self.ac.employee_repo, name): return getattr(self.ac.employee_repo, name)
        if hasattr(self.ac.inventory_repo, name): return getattr(self.ac.inventory_repo, name)
        if hasattr(self.ac.order_repo, name): return getattr(self.ac.order_repo, name)
        if hasattr(self.menu, name): return getattr(self.menu, name)
        if hasattr(self.attendance, name): return getattr(self.attendance, name)
        raise AttributeError(f"Ningun repositorio tiene el metodo {name}")

class AppController(QObject):
    
    lista_empleados_actualizada = pyqtSignal()
    ordenes_actualizadas = pyqtSignal()
    asistencia_recibida = pyqtSignal(dict)
    error_ocurrido = pyqtSignal(str)

    emit_to_server = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()
        from src.database.repositories.employees import employee_repo
        from src.services.order_service import order_service
        from src.database.repositories.inventory import inventory_repo
        from src.database.repositories.orders import order_repo
        self.employee_repo = employee_repo
        self.order_service = order_service
        self.inventory_repo = inventory_repo
        self.order_repo = order_repo
        self.data_manager = LegacyDataManager(self)
        
        self.threadpool = QThreadPool()
        logger.info(f"Multithreading con un maximo de {self.threadpool.maxThreadCount()} hilos")
        
        self.config = self._load_config()
        self.API_KEY = self.config.get("api_key", "puestito_seguro_2025")
        self.SERVER_URL = self.config.get("server_url", "http://127.0.0.1:5000")
        self.printer_service = PrinterService(self)
        self.notification_service = notification_service
        logger.info(f"[AppController] Inicializado.")

    def get_config(self):
        return self.config

    def _load_config(self):
        try:
            config_path = get_persistent_path("config.json")
            
            if not os.path.exists(config_path):
                logger.warning(f"No se encontro {config_path}")
                return {}
                
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando configuracion en Controller: {e}")
            return {}

    def get_todos_los_empleados(self):
        return self.employee_repo.get_employees()

    def agregar_empleado(self, new_id, new_name, new_rol, fingerprint_id=None):
        try:
            result = self.employee_repo.add_employee(new_id, new_name, new_rol, fingerprint_id)
            if result: self.lista_empleados_actualizada.emit()
            return result
        except Exception as e:
            self.error_ocurrido.emit(f"Error agregando empleado: {e}")
            return False

    def editar_empleado(self, original_id, new_id, new_name, new_rol, fingerprint_id=None):
        try:
            result = self.employee_repo.update_employee(original_id, new_id, new_name, new_rol, fingerprint_id)
            if result: self.lista_empleados_actualizada.emit()
            return result
        except Exception as e:
            self.error_ocurrido.emit(f"Error editando empleado: {e}")
            return False

    def eliminar_empleado(self, employee_id):
        try:
            result = self.employee_repo.delete_employee(employee_id)
            if result: self.lista_empleados_actualizada.emit()
            return result
        except Exception as e:
            self.error_ocurrido.emit(f"Error eliminando empleado: {e}")
            return False
    
    def save_config_to_file(self, config_data):
        import json
        import os
        from path_manager import get_persistent_path
        
        config_path = get_persistent_path("config.json")
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            self.config = config_data
            self.printer_service.invalidate_cache()
            logger.info("Configuracion guardada en config.json")
            return True
        except Exception as e:
            logger.critical(f"Error guardando config.json: {e}")
            return False

    def notify_server_config_change(self):
        self.notificar_evento_servidor("config_update")

    def notificar_evento_servidor(self, nombre_evento, payload_data=None):
        self.emit_to_server.emit(nombre_evento, payload_data or {})
    
    def procesar_nueva_orden(self, orden_completa):
        logger.info("[Controller] Procesando nueva orden...")
        try:
            nuevo_id = self.order_service.create_new_order(orden_completa)
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
            orden_cerrada = self.order_service.complete_order(mesa_key)
            if orden_cerrada:
                logger.info(f"Mesa {mesa_key} cerrada en BD.")
                
                # Async I/O for printer
                worker = Worker(self._tarea_impresion_cierre, order_data)
                self.threadpool.start(worker)
                
                self.ordenes_actualizadas.emit()
                self.notificar_cambios_mesas()
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error al cobrar cuenta: {e}")
            return False

    def _tarea_impresion_cierre(self, order_data):
        self.printer_service.open_cash_drawer()
        if order_data:
            self.printer_service.print_receipt(order_data)

    def registrar_impresion_proforma(self, mesa_key):
        return self.order_repo.registrar_impresion_proforma(mesa_key)

    def notificar_cambios_mesas(self):
        self.notificar_evento_servidor("mesas_update")

    def notificar_alerta_kds(self, mesa_key, destino):
        mensaje = f"Mesa {mesa_key}: Pedido de {destino} listo"
        
        payload_data = {
            'mesa_key': str(mesa_key),
            'destino': str(destino),
            'mensaje': mensaje
        }
        
        self.notificar_evento_servidor("alerta_orden_lista", payload_data)

        # Envio a Firebase asincrono
        worker = Worker(self.notification_service.enviar_notificacion_tema, "alertas_puestito", "Orden Lista", mensaje)
        self.threadpool.start(worker)

    def procesar_item_individual_listo(self, id_detalle, mesa_key, destino):
        try:
            resultado = self.order_service.mark_individual_item_ready(id_detalle)
            if resultado:
                self.ordenes_actualizadas.emit()
                self.notificar_cambios_mesas()
                self.notificar_alerta_kds(mesa_key, destino)
                return True
            return False
        except Exception as e:
            logger.error(f"Error procesando item listo: {e}")
            return False
        
    def formatear_sensor_biometrico(self):
        self.notificar_evento_servidor("api/biometric/start-clear")

    def get_inventario(self):
        return self.inventory_repo.get_inventario_completo()

    def agregar_al_inventario(self, nombre, cantidad, es_auto, id_menu=None):
        try:
            return self.inventory_repo.agregar_item_inventario(nombre, cantidad, es_auto, id_menu)
        except Exception as e:
            self.error_ocurrido.emit(f"Error inventario: {e}")
            return False

    def actualizar_stock(self, id_inv, cantidad):
        try:
            return self.inventory_repo.actualizar_cantidad_inventario(id_inv, cantidad)
        except Exception as e:
            self.error_ocurrido.emit(f"Error inventario: {e}")
            return False

    def eliminar_del_inventario(self, id_inv):
        try:
            return self.inventory_repo.eliminar_item_inventario(id_inv)
        except Exception as e:
            self.error_ocurrido.emit(f"Error inventario: {e}")
            return False