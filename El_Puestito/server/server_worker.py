# server/server_worker.py
import os
import sys
import json
import socket
import io
import datetime
import requests
import eventlet
import eventlet.wsgi

from PyQt6.QtCore import QObject, pyqtSignal

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ServerWorker(QObject):

    class ServerShutdownException(Exception):
        """Excepción personalizada para detener el servidor limpiamente."""
        pass

    asistencia_recibida = pyqtSignal(dict)
    nueva_orden_recibida = pyqtSignal(dict)

    def stop_server(self):
        """
        Detiene el servidor SocketIO.
        Se llama desde el Hilo Principal.
        """
        print("[Servidor] Recibida orden de 'stop_server' desde MainThread.")
        print("[Servidor] Enviando petición HTTP /shutdown a mí mismo...")
        try:
            requests.post('http://127.0.0.1:5000/shutdown')
            print("[Servidor] Petición /shutdown enviada.")
            
        except requests.exceptions.RequestException as e:
            print(f"[Servidor] No se pudo enviar /shutdown, quizás ya estaba detenido: {e}")
        except Exception as e:
            print(f"[Servidor] Error al enviar /shutdown: {e}")

    def _delayed_shutdown(self):
        """
        Helper que se ejecuta en un greenlet separado para apagar el servidor.
        """
        print("[Servidor] Greenlet iniciado, esperando 0.1s para apagar...")
        eventlet.sleep(0.1) 
        try:
            print("[Servidor] Greenlet: Llamando a self.socketio.stop()...")
            self.socketio.stop()
            print("[Servidor] Greenlet: self.socketio.stop() llamado exitosamente.")
        except Exception as e:
            print(f"[Servidor] Greenlet: Error al llamar a self.socketio.stop(): {e}")

    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager 
        
        self.app = Flask(__name__)
        
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='eventlet')
        self.server_instance = None
        
        worker_self = self

        @self.app.route('/shutdown', methods=['POST'])
        def shutdown():
            """
            Esta es la ruta 'educada' que responde OK y luego se apaga.
            """
            print("[Servidor] Recibida orden de apagado (Modo Eventlet 'Educado')...")
            
            eventlet.spawn(worker_self._delayed_shutdown) 
            
            print("[Servidor] Respondiendo 200 OK y programando apagado.")
            return jsonify({"status": "shutdown_initiated"})


        @self.app.route('/registrar', methods=['POST'])
        def registrar_asistencia_movil():
            data = request.json
            print("-----------------------------------------")
            print(f"[Asistencia Móvil] Datos recibidos: {data}")

            if not data or 'employee_id' not in data or 'deviceId' not in data:
                print("[Asistencia Móvil] Error: Datos incompletos.")
                return jsonify({"error": "Datos incompletos"}), 400

            employee_id = data['employee_id']
            device_id = data['deviceId']
            
            empleado_con_dispositivo = self.data_manager.get_employee_by_device(device_id)
            if empleado_con_dispositivo and empleado_con_dispositivo['id_empleado'] != employee_id:
                print(f"[Asistencia Móvil] ⚠️ Dispositivo {device_id} ya vinculado a {empleado_con_dispositivo.get('nombre')}, ignorando duplicado.")
                return jsonify({
                    "error": "device_in_use",
                    "message": f"Este dispositivo ya fue usado por {empleado_con_dispositivo.get('nombre')}. Cada dispositivo puede registrar solo a una persona."
                }), 403

            empleado_encontrado = self.data_manager.get_employee_by_id(employee_id)

            if not empleado_encontrado:
                print(f"[Asistencia Móvil] Error: Empleado con ID {employee_id} no encontrado.")
                return jsonify({"error": "not_found", "message": "Empleado no encontrado en la base de datos."}), 404
            
            timestamp_actual = datetime.datetime.now().isoformat(timespec='seconds')
            
            if not empleado_encontrado.get("deviceId"):
                print(f"[Asistencia Móvil] Vinculando dispositivo {device_id} a {empleado_encontrado['nombre']}...")
                
                self.data_manager.link_device_to_employee(employee_id, device_id)
                event_type = "entrada"
                self.data_manager.add_attendance_event(employee_id, event_type, timestamp_actual)

                self.asistencia_recibida.emit({
                    "employee_id": employee_id,
                    "event_type": event_type,
                    "timestamp": timestamp_actual
                }) 

                print("[Asistencia Móvil] Dispositivo vinculado y asistencia registrada.")
                return jsonify({
                    "status": "success",
                    "message": f"Dispositivo registrado a {empleado_encontrado['nombre']}. Asistencia marcada."
                }), 201 

            elif empleado_encontrado.get("deviceId") == device_id:
                print(f"[Asistencia Móvil] Asistencia normal para {empleado_encontrado['nombre']}.")

                last_event = self.data_manager.get_last_attendance_event(employee_id)
                event_type = "salida" if last_event and last_event['tipo'] == 'entrada' else 'entrada'
                
                if event_type == "entrada":
                    print(f"----> Marcando ENTRADA (BD): {timestamp_actual}")
                else:
                    print(f"----> Marcando SALIDA (BD): {timestamp_actual}")

                self.data_manager.add_attendance_event(employee_id, event_type, timestamp_actual)
                
                self.asistencia_recibida.emit({
                    "employee_id": employee_id,
                    "event_type": event_type,
                    "timestamp": timestamp_actual
                })

                return jsonify({
                    "status": "success",
                    "message": f"Asistencia de {empleado_encontrado['nombre']} registrada correctamente."
                }), 200

            else:
                print(f"[Asistencia Móvil] Error de Fraude: ID {employee_id} ({empleado_encontrado['nombre']}) intentó registrarse con dispositivo diferente.")
                return jsonify({
                    "error": "device_mismatch",
                    "message": "Este dispositivo no coincide con el registrado para este empleado. Contacte al administrador."
                }), 403
        
        @self.app.route('/configuracion', methods=['GET'])
        def get_configuracion():
            """Lee el archivo config.json y lo devuelve."""
            try:
                config_path = os.path.join(BASE_DIR, "assets", "config.json")
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                return jsonify(config_data)
            except Exception as e:
                print(f"❌ Error al leer config.json: {e}")
                return jsonify({"error": "No se pudo cargar la configuración"}), 500
            
        @self.app.route('/images/<path:filename>')
        def serve_image(filename):
            """
            Sirve una imagen desde la carpeta assets.
            """
            image_directory = os.path.join(BASE_DIR, "assets")
            try:
                return send_from_directory(image_directory, filename, as_attachment=False)
            except FileNotFoundError:
                return jsonify({"error": "Image not found"}), 404
            
        @self.app.route('/menu', methods=['GET'])
        def get_menu():
            """Lee el menú desde la BD, filtra los no disponibles y lo devuelve."""
            try:
                menu_data = worker_self.data_manager.get_menu_with_categories()
                
                menu_filtrado = {"categorias": []}
                
                for categoria_original in menu_data.get("categorias", []):
                    items_disponibles = [
                        item for item in categoria_original.get("items", [])
                        if item.get("disponible", True) 
                    ]
                    
                    if items_disponibles:
                        nueva_categoria = categoria_original.copy()
                        
                        items_app_format = []
                        for item in items_disponibles:
                            item_copy = item.copy()
                            item_copy['id'] = item_copy.pop('id_item', item_copy.get('id'))
                            items_app_format.append(item_copy)
                        
                        nueva_categoria["items"] = items_app_format
                        menu_filtrado["categorias"].append(nueva_categoria)
                
                return jsonify(menu_filtrado)
            except Exception as e:
                print(f"❌ Error al leer o filtrar menú desde la BD: {e}")
                return jsonify({"error": "No se pudo cargar el menú"}), 500
            
        @self.app.route('/nueva-orden', methods=['POST'])
        def recibir_orden():
            orden = request.json
            mesas_enlazadas = orden.get('mesas_enlazadas')
            if mesas_enlazadas:
                print(f"🔗 Orden para Mesa {orden.get('numero_mesa')} incluye grupo: {mesas_enlazadas}")
            
            is_valid, error_msg = worker_self._validate_order_items(orden)
            if not is_valid:
                print(f"❌ Orden Rechazada: {error_msg}")
                return jsonify({
                    "error": "Item Agotado",
                    "mensaje": error_msg
                }), 400
            
            order_id = orden.get("order_id")
            if worker_self.data_manager.check_duplicate_order_id(order_id):
                print(f"📦 Ignorando orden duplicada con ID: {order_id}")
                return jsonify({"status": "ok_duplicate"}), 200
            
            print(f"📦 Nueva orden recibida con ID: {order_id}. Pasando al hilo principal...")
            worker_self.nueva_orden_recibida.emit(orden) 
            return jsonify({"status": "ok_new"}), 200
        
        @self.app.route('/employees', methods=['GET'])
        def get_employees():
            employees_full = worker_self.data_manager.get_employees() 
            if employees_full is None:
                return jsonify({"error": "No se pudo cargar la lista de empleados"}), 500
            
            employee_list = [
                {"id": emp.get("id_empleado"), "nombre": emp.get("nombre")}
                for emp in employees_full
                if emp.get("id_empleado") and emp.get("nombre") 
            ]
            return jsonify(employee_list)
        
        @self.app.route('/estado-mesas', methods=['GET'])
        def get_estado_mesas():
            try:
                caja_data = worker_self.data_manager.get_active_orders_caja()
                print(f"📊 Estado de mesas solicitado. Enviando objeto de caja desde la BD.")
                return jsonify(caja_data)
            except Exception as e:
                print(f"❌ Error al leer estado de mesas desde la BD: {e}")
                return jsonify({"error": "No se pudo cargar el estado de las mesas"}), 500
            

        @self.app.route('/trigger_update', methods=['POST'])
        def trigger_update():
            data = request.json
            event_name = data.get('event')
            payload = {}

            if event_name == 'mesas_actualizadas':
                
                eventlet.sleep(0.1) 
                
                table_state_payload = worker_self._get_table_state()
                worker_self.socketio.emit('mesas_actualizadas', table_state_payload)
                print(f"📣 Emitiendo 'mesas_actualizadas' a los clientes (Mesa Cobrada) con datos: {payload}")
                
                
            elif event_name == 'menu_actualizado':
                worker_self.socketio.emit('menu_actualizado', {'mensaje': 'Menú cambiado'})
                print("📣 Emitiendo 'menu_actualizado' a los clientes (Menú Editado)") 
            
            return jsonify({"status": "emitted"}), 200
            
    
    def _get_table_state(self):
        """Lee el estado de caja desde la BD y devuelve el objeto de órdenes activas."""
        try:
            caja_data = self.data_manager.get_active_orders_caja()
            return caja_data 
        except Exception as e:
            print(f"❌ Error al leer estado de caja desde BD para socket: {e}")
            return {}
        

    def _validate_order_items(self, orden):
        """Valida los IDs de una orden contra los items disponibles en la BD."""
        try:
            menu_data = self.data_manager.get_menu_with_categories()
            
            available_ids = set()
            for categoria in menu_data.get("categorias", []):
                for item in categoria.get("items", []):
                    if item.get("disponible", True) and item.get("id_item"):
                        available_ids.add(item.get("id_item"))
            
            items_en_orden = orden.get("items", [])
            for item_in_order in items_en_orden:
                item_id = item_in_order.get("item_id") 
                if item_id not in available_ids:
                    item_nombre = item_in_order.get("nombre", "Desconocido")
                    return False, f"El platillo '{item_nombre}' ya no está disponible."
            return True, ""
        except Exception as e:
            print(f"❌ Error al validar la orden contra la BD: {e}")
            return False, "Error interno al validar el menú."
        
        
    def start_server(self):
        print("🚀 Iniciando servidor Flask con SocketIO (Modo: threading)...")
        try:
            self.socketio.run(self.app, 
                            host='0.0.0.0', 
                            port=5000, 
                            allow_unsafe_werkzeug=True,
                            log_output=False) 

        except Exception as e:
            if "Interrupted" in str(e) or "SystemExit" in str(e):
                print("ℹ️ Servidor detenido limpiamente (modo eventlet/threading).")
            else:
                print(f"❌ CRASH del Servidor SocketIO: {e}")
        finally:
            print("🛑 El método start_server() del worker ha finalizado.")