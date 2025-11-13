import sys
import os
import json
import qrcode
import socket
import io
import datetime 
import random
from fpdf import FPDF
from PyQt6.QtWidgets import QDialog 
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QLineEdit, QFrame, QHeaderView,
    QTableWidgetItem, QStackedWidget, QGraphicsOpacityEffect,QDialog,
    QScrollArea, QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
    QTabWidget, QGridLayout, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QCheckBox,QGraphicsOpacityEffect, QTreeWidgetItemIterator, 
    QCalendarWidget,QDateEdit, QFileDialog)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import (
    Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QRect,
    QSequentialAnimationGroup, QParallelAnimationGroup, QTimer, QDate, QObject, QThread, pyqtSignal,
    pyqtSlot)
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from flask import Flask, request, jsonify, send_from_directory
import eventlet
import eventlet.wsgi
import datetime 
from PyQt6.QtWidgets import QScrollArea, QFrame, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from flask_socketio import SocketIO
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class QRCodeDialog(QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ordenes_activas = {}
        self.ventas_file_path = os.path.join(BASE_DIR, "assets", "ventas_completadas.json")
        self.setWindowTitle("Conexión del Servidor")
        self.setFixedSize(300, 350)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction_label = QLabel("Escanea este código desde la app del teléfono:")
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(250, 250)
        layout.addWidget(instruction_label)
        layout.addWidget(self.qr_label)
        self.generate_and_display_qr()

    def get_local_ip(self):
        """Encuentra la dirección IP local de la computadora."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP
    
    def generate_and_display_qr(self):
        ip_address = self.get_local_ip()
        server_url = f"http://{ip_address}:5000"
        
        print(f"🖥️  Generando QR para la dirección: {server_url}")
        qr_image = qrcode.make(server_url)
        
        buffer = io.BytesIO()
        qr_image.save(buffer, "PNG")
        
        buffer.seek(0)
        
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        self.qr_label.setPixmap(pixmap.scaled(250, 250))

class OrderTicketWidget(QFrame):
    orden_lista = pyqtSignal(QWidget)

    def __init__(self, orden_data, parent=None):
        super().__init__(parent)
        self.setObjectName("order_ticket")
        self.setFixedWidth(300)
        self.ticket_widget = self
        layout = QVBoxLayout(self)
        mesa_label = QLabel(f"Mesa: {orden_data['numero_mesa']}")
        mesa_label.setObjectName("ticket_title")
        layout.addWidget(mesa_label)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        for item in orden_data['items']:
            item_layout = QHBoxLayout()
            img_label = QLabel()
            img_label.setFixedSize(64, 64)
            imagen_nombre = item.get("imagen", "")
            if imagen_nombre:
                imagen_path = os.path.join(BASE_DIR, "assets", imagen_nombre)
                pixmap = QPixmap(imagen_path)
                img_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            item_layout.addWidget(img_label)
            text_layout = QVBoxLayout()
            cantidad = item['cantidad']
            nombre = item['nombre']
            notas = f"({item['notas']})" if item['notas'] else ""
            
            nombre_label = QLabel(f"{cantidad}x {nombre}")
            nombre_label.setObjectName("ticket_item_title")
            nombre_label.setWordWrap(True)
            notas_label = QLabel(notas)
            notas_label.setObjectName("ticket_item_notes")
            notas_label.setWordWrap(True)
            text_layout.addWidget(nombre_label)
            if notas:
                text_layout.addWidget(notas_label)
            
            item_layout.addLayout(text_layout)
            layout.addLayout(item_layout)
        
        listo_button = QPushButton("Listo")
        listo_button.setObjectName("orange_button")
        listo_button.clicked.connect(self.marcar_como_lista) # Esta línea ahora funcionará
        layout.addWidget(listo_button)

    def marcar_como_lista(self):
        """ Emite la señal con una referencia a este mismo widget para que pueda ser eliminado """
        self.orden_lista.emit(self.ticket_widget)

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

    def __init__(self):
        super().__init__()
        self.app = Flask(__name__)
        
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='eventlet')
        self.asistencia_file_path = os.path.join(BASE_DIR, "assets", "asistencia.json")
        self.asistencia_historico_path = os.path.join(BASE_DIR, "assets", "asistencia_historico.json")
        self.ids_file_path = os.path.join(BASE_DIR, "assets", "processed_orders.json")
        self.ids_file_path = os.path.join(BASE_DIR, "assets", "processed_orders.json")
        try:
            with open(self.ids_file_path, "r") as f:
                self.processed_order_ids = json.load(f)
            print(f"✅ IDs de órdenes prevas cargados desde {self.ids_file_path}")
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ No se encontró archivo de IDs de órdenes, iniciando lista vacía.")
            self.processed_order_ids = []
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

            employees = worker_self._load_employee_data()
            
            if employees is None:
                print("[Asistencia Móvil] Error: No se pudo cargar el archivo de empleados.")
                return jsonify({"error": "Error interno del servidor (BD)"}), 500

            empleado_encontrado = None

            for emp in employees:
                # Solo impedir si el mismo dispositivo intenta registrar otro empleado distinto
                if emp.get("deviceId") == device_id and emp.get("id") != employee_id:
                    print(f"[Asistencia Móvil] ⚠️ Dispositivo {device_id} ya vinculado a {emp.get('nombre')}, ignorando duplicado.")
                    return jsonify({
                        "error": "device_in_use",
                        "message": f"Este dispositivo ya fue usado por {emp.get('nombre')}. Cada dispositivo puede registrar solo a una persona."
                    }), 403


                if emp.get("id") == employee_id:
                    empleado_encontrado = emp
            if not empleado_encontrado:
                print(f"[Asistencia Móvil] Error: Empleado con ID {employee_id} no encontrado.")
                return jsonify({"error": "not_found", "message": "Empleado no encontrado en la base de datos."}), 404
            
            if empleado_encontrado.get("deviceId") is None:
                print(f"[Asistencia Móvil] Vinculando dispositivo {device_id} a {empleado_encontrado['nombre']}...")
                empleado_encontrado["deviceId"] = device_id
                timestamp_actual = datetime.datetime.now().isoformat(timespec='seconds') 
                empleado_encontrado["entrada"] = timestamp_actual 
                empleado_encontrado["salida"] = "-" 
                empleado_encontrado["estado"] = "Presente"

                worker_self._log_attendance_event(employee_id, "entrada")
                if not worker_self._save_employee_data(employees):
                    return jsonify({"error": "Error interno al guardar"}), 500
                
                worker_self.asistencia_recibida.emit({"employee_id": employee_id}) 

                print("[Asistencia Móvil] Dispositivo vinculado y asistencia registrada.")
                return jsonify({
                    "status": "success",
                    "message": f"Dispositivo registrado a {empleado_encontrado['nombre']}. Asistencia marcada."
                }), 201 # Creado

            elif empleado_encontrado.get("deviceId") == device_id:
                
                print(f"[Asistencia Móvil] Asistencia normal para {empleado_encontrado['nombre']}.")

                timestamp_actual = datetime.datetime.now().isoformat(timespec='seconds') 
                entrada_actual = empleado_encontrado.get("entrada", "-")
                salida_actual = empleado_encontrado.get("salida", "-") 
                event_type = ""
                if entrada_actual == "-" or not entrada_actual or (salida_actual != "-" and salida_actual):
                    empleado_encontrado["entrada"] = timestamp_actual
                    empleado_encontrado["salida"] = "-" 
                    empleado_encontrado["estado"] = "Presente"
                    event_type = "entrada" # Guardamos el tipo de evento
                    print(f"----> Marcando ENTRADA: {timestamp_actual}")
                else: 
                    empleado_encontrado["salida"] = timestamp_actual
                    empleado_encontrado["estado"] = "Ausente"
                    event_type = "salida" # Guardamos el tipo de evento
                    print(f"----> Marcando SALIDA: {timestamp_actual}")

                if event_type: # Solo si hubo un evento válido
                    worker_self._log_attendance_event(employee_id, event_type)

                if not worker_self._save_employee_data(employees):
                    return jsonify({"error": "Error interno al guardar"}), 500

                worker_self.asistencia_recibida.emit({"employee_id": employee_id})

                return jsonify({
                    "status": "success",
                    "message": f"Asistencia de {empleado_encontrado['nombre']} registrada correctamente."
                }), 200

            else:
                
                print(f"[Asistencia Móvil] Error de Fraude: ID {employee_id} ({empleado_encontrado['nombre']}) intentó registrarse con dispositivo diferente.")
                return jsonify({
                    "error": "device_mismatch",
                    "message": "Este dispositivo no coincide con el registrado para este empleado. Contacte al administrador."
                }), 403 # 
        
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
            """Lee el archivo menu.json, filtra los no disponibles y lo devuelve."""
            try:
                menu_path = os.path.join(BASE_DIR, "assets", "menu.json")
                with open(menu_path, 'r', encoding='utf-8') as f:
                    menu_data = json.load(f)
                menu_filtrado = {"categorias": []}
                
                for categoria_original in menu_data.get("categorias", []):
                    items_disponibles = [
                        item for item in categoria_original.get("items", [])
                        if item.get("disponible", True) # Si no existe la llave, es True
                    ]
                    
                    if items_disponibles:
                        nueva_categoria = categoria_original.copy() # Copia superficial
                        nueva_categoria["items"] = items_disponibles
                        menu_filtrado["categorias"].append(nueva_categoria)
                
                return jsonify(menu_filtrado)
            except Exception as e:
                print(f"❌ Error al leer o filtrar menu.json: {e}")
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
            if order_id in worker_self.processed_order_ids:
                print(f"📦 Ignorando orden duplicada con ID: {order_id}")
                return jsonify({"status": "ok_duplicate"}), 200
            worker_self.processed_order_ids.append(order_id)
            if len(worker_self.processed_order_ids) > 200:
                worker_self.processed_order_ids.pop(0)
            print(f"📦 Nueva orden recibida con ID: {order_id}")
            
            worker_self.nueva_orden_recibida.emit(orden) 
            
            eventlet.sleep(0.1) 
            
            table_state_payload = worker_self._get_table_state()
            worker_self.socketio.emit('mesas_actualizadas', table_state_payload)
            print(f"📣 Emitiendo 'mesas_actualizadas' a los clientes...")
            
            return jsonify({"status": "ok_new"}), 200
        
        @self.app.route('/employees', methods=['GET'])

        def get_employees():

            employees_full = worker_self._load_employee_data()
            if employees_full is None:
                return jsonify({"error": "No se pudo cargar la lista de empleados"}), 500
            employee_list = [
                {"id": emp.get("id"), "nombre": emp.get("nombre")}
                for emp in employees_full
                if emp.get("id") and emp.get("nombre") 
            ]
            
            return jsonify(employee_list)
        
        @self.app.route('/estado-mesas', methods=['GET'])

        def get_estado_mesas():
            try:
                caja_path = os.path.join(BASE_DIR, "assets", "caja_ordenes.json")
                with open(caja_path, 'r', encoding='utf-8') as f:
                    caja_data = json.load(f)
                
                mesas_ocupadas = list(caja_data.keys())
                print(f"📊 Estado de mesas solicitado. Enviando objeto de caja completo.")
                return jsonify(caja_data)
            except FileNotFoundError:
                print("📊 Estado de mesas solicitado. No se encontró caja_ordenes.json, devolviendo vacío.")
                return jsonify({})
            except Exception as e:
                print(f"❌ Error al leer caja_ordenes.json: {e}")
                return jsonify({"error": "No se pudo cargar el estado de las mesas"}), 500
            

        @self.app.route('/trigger_update', methods=['POST'])
        def trigger_update():
            data = request.json
            event_name = data.get('event')
            payload = {} # Payload por defecto

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
        """Lee el JSON de caja y devuelve el objeto completo de órdenes activas."""
        try:
            caja_path = os.path.join(BASE_DIR, "assets", "caja_ordenes.json")
            with open(caja_path, 'r', encoding='utf-8') as f:
                caja_data = json.load(f)
            return caja_data 
        except Exception as e:
            print(f"❌ Error al leer caja_ordenes.json para socket: {e}")
            return {} 

    def _load_employee_data(self):
        """Carga los datos de los empleados desde el JSON."""
        if not os.path.exists(self.asistencia_file_path):
            print(f"Error CRÍTICO: No se encuentra el archivo en: {self.asistencia_file_path}")
            return None
        try:
            with open(self.asistencia_file_path, "r", encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error al leer el JSON de asistencia: {e}")
            return None

    def _save_employee_data(self, data):
        """Guarda los datos de los empleados en el JSON."""
        try:
            with open(self.asistencia_file_path, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"💾 Datos de asistencia guardados en {self.asistencia_file_path}")
            return True
        except IOError as e:
            print(f"Error al guardar el archivo de asistencia: {e}")
            return False
        
    def _log_attendance_event(self, employee_id, event_type):
        """Añade un registro al archivo de historial de asistencia."""
        log_entry = {
            "employee_id": employee_id,
            "timestamp": datetime.datetime.now().isoformat(timespec='seconds'),
            "type": event_type # Será "entrada" o "salida"
        }
        
        history = []
        try:
            with open(self.asistencia_historico_path, "r", encoding='utf-8') as f:
                history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            history = [] 
            
        history.append(log_entry)
        
        try:
            with open(self.asistencia_historico_path, "w", encoding='utf-8') as f:
                json.dump(history, f, indent=4, ensure_ascii=False)
            print(f"🕒 Evento '{event_type}' guardado en historial para ID {employee_id}.")
            return True
        except IOError as e:
            print(f"❌ Error al guardar en historial de asistencia: {e}")
            return False    

    def _validate_order_items(self, orden):
        try:
            menu_path = os.path.join(BASE_DIR, "assets", "menu.json")
            with open(menu_path, 'r', encoding='utf-8') as f:
                menu_data = json.load(f)
            available_ids = set()
            for categoria in menu_data.get("categorias", []):
                for item in categoria.get("items", []):
                    if item.get("disponible", True) and item.get("id"):
                        available_ids.add(item.get("id"))
            items_en_orden = orden.get("items", [])
            for item_in_order in items_en_orden:
                item_id = item_in_order.get("item_id") 
                if item_id not in available_ids:
                    item_nombre = item_in_order.get("nombre", "Desconocido")
                    return False, f"El platillo '{item_nombre}' ya no está disponible."
            return True, ""
        except Exception as e:
            print(f"❌ Error al validar la orden: {e}")
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
            # Esta lógica de captura de SystemExit es correcta
            if "Interrupted" in str(e) or "SystemExit" in str(e):
                print("ℹ️ Servidor detenido limpiamente (modo eventlet/threading).")
            else:
                print(f"❌ CRASH del Servidor SocketIO: {e}")
        finally:
            print("🛑 El método start_server() del worker ha finalizado.")

    def save_ids_to_file(self):
        try:
            with open(self.ids_file_path, "w") as f:
                json.dump(self.processed_order_ids, f)
                print(f"💾 IDs de órdenes guardados en {self.ids_file_path}")
        except IOError:
            print("❌ Error al guardar los IDs de las órdenes.")
            
    def _validate_order_items(self, orden):
        try:
            menu_path = os.path.join(BASE_DIR, "assets", "menu.json")
            with open(menu_path, 'r', encoding='utf-8') as f:
                menu_data = json.load(f)
            available_ids = set()
            for categoria in menu_data.get("categorias", []):
                for item in categoria.get("items", []):
                    if item.get("disponible", True) and item.get("id"):
                        available_ids.add(item.get("id"))
            items_en_orden = orden.get("items", [])
            for item_in_order in items_en_orden:
                item_id = item_in_order.get("item_id") 
                if item_id not in available_ids:
                    item_nombre = item_in_order.get("nombre", "Desconocido")
                    return False, f"El platillo '{item_nombre}' ya no está disponible."
            return True, ""
        except Exception as e:
            print(f"❌ Error al validar la orden: {e}")
            return False, "Error interno al validar el menú."
        
class ServerThread(QThread):
        def __init__(self, worker_instance, parent=None):
            super().__init__(parent)
            # Recibe el worker que debe ejecutar
            self.worker = worker_instance

        def run(self):
            """Este es el código que se ejecuta en el hilo separado."""
            print("[ServerThread] Hilo iniciado, llamando a worker.start_server()...")
            self.worker.start_server() # Esta es la llamada bloqueante
            print("[ServerThread] worker.start_server() ha terminado. Hilo finalizando.")        


class AttendancePage(QWidget):
    """La vista de control de asistencia que ya teníamos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 25)
        main_layout.setSpacing(20)
        controls_layout = self.create_controls_bar()
        table_title = QLabel("Lista de Empleados")
        table_title.setObjectName("section_title")
        self.employee_table = self.create_employee_table()
        main_layout.addLayout(controls_layout)
        self.btn_limpiar.clicked.connect(self.limpiar_registros)
        main_layout.addWidget(table_title)
        main_layout.addWidget(self.employee_table) # Usamos la variable de instancia

    def refresh_attendance_table(self, employee_data_list):
        """Limpia y vuelve a llenar la tabla de asistencia con los datos proporcionados."""
        self.employee_table.setRowCount(0) # Limpiamos la tabla
        self.employee_table.setRowCount(len(employee_data_list))
        for row, employee_data in enumerate(employee_data_list):
            item_nombre = QTableWidgetItem(employee_data["nombre"])
            item_nombre.setData(Qt.ItemDataRole.UserRole, employee_data["id"])
            self.employee_table.setItem(row, 0, item_nombre)
            self.employee_table.setItem(row, 1, QTableWidgetItem(employee_data["entrada"]))
            self.employee_table.setItem(row, 2, QTableWidgetItem(employee_data["salida"]))
            status_txt = employee_data["estado"]
            cell_widget = QWidget()
            h_layout = QHBoxLayout(cell_widget)
            h_layout.setContentsMargins(8, 0, 0, 0)
            h_layout.setSpacing(10)
            h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            dot = QLabel()
            dot.setObjectName("status_indicator")
            dot.setFixedSize(14, 14)
            dot.setProperty("status", "present" if status_txt.lower().startswith("pres") else "absent")
            text = QLabel(status_txt)
            text.setObjectName("status_text")
            h_layout.addWidget(dot)
            h_layout.addWidget(text)
            self.employee_table.setCellWidget(row, 3, cell_widget)

    def update_employee_data(self, new_data):
        """Actualiza la lista interna de datos y refresca la tabla."""
        try:
            with open(self.data_file, "w") as f:
                json.dump(new_data, f, indent=4)
                print(f"💾 Datos de asistencia actualizados y guardados desde Admin.")
            self.refresh_attendance_table(new_data) # Llama a la función de refresco
        except IOError:
            print(f"❌ Error: No se pudo guardar el archivo de datos actualizado.")
        except AttributeError:
            print("❌ Error: data_file no está definido.")

    def create_controls_bar(self):
        controls_layout = QHBoxLayout()
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Buscar empleado...")
        search_bar.setObjectName("search_bar")
        self.btn_limpiar = QPushButton("Limpiar Registros")
        self.btn_limpiar.setObjectName("orange_button") 
        self.btn_limpiar.setFixedWidth(180) 
        controls_layout.addWidget(search_bar)
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_limpiar) 
        return controls_layout
    
    def registrar_asistencia(self, datos):
        id_empleado_recibido = datos.get("employee_id")
        if not id_empleado_recibido:
            return
        
        for fila in range(self.employee_table.rowCount()):
            item_nombre = self.employee_table.item(fila, 0)
            id_guardado = item_nombre.data(Qt.ItemDataRole.UserRole)
            
            if id_guardado == id_empleado_recibido:
                hora_actual = datetime.datetime.now().strftime("%I:%M %p")
                new_status_text = ""
                new_status_property = ""
                
                celda_entrada_item = self.employee_table.item(fila, 1)
                entrada_esta_vacia = (celda_entrada_item is None) or \
                                    (celda_entrada_item.text() == "-") or \
                                    (not celda_entrada_item.text())
                
                # Leemos el estado actual *antes* de cambiarlo
                celda_salida_item = self.employee_table.item(fila, 2)
                salida_esta_llena = (celda_salida_item is not None) and \
                                (celda_salida_item.text() != "-") and \
                                (celda_salida_item.text())

                if entrada_esta_vacia or salida_esta_llena:
                    self.employee_table.setItem(fila, 1, QTableWidgetItem(hora_actual))
                    self.employee_table.setItem(fila, 2, QTableWidgetItem("-")) # Limpiamos salida por si acaso
                    new_status_text = "Presente"
                    new_status_property = "present" # Esto pondrá el punto verde
                    self.employees_data[fila]["entrada"] = hora_actual
                    self.employees_data[fila]["salida"] = "-" # Aseguramos limpiar salida
                    self.employees_data[fila]["estado"] = "Presente"
                else:
                    self.employee_table.setItem(fila, 2, QTableWidgetItem(hora_actual))
                    new_status_text = "Ausente"
                    new_status_property = "absent" # Esto pondrá el punto rojo
                    self.employees_data[fila]["salida"] = hora_actual
                    self.employees_data[fila]["estado"] = "Ausente"

                widget_estado = self.employee_table.cellWidget(fila, 3)
                
                if widget_estado:
                    dot = widget_estado.findChild(QLabel, "status_indicator")
                    text = widget_estado.findChild(QLabel, "status_text")
                    if dot:
                        dot.setProperty("status", new_status_property)
                        dot.style().polish(dot) # Actualiza el estilo del widget
                    if text:
                        text.setText(new_status_text)
                
                print(f"✅ Tabla actualizada para empleado con ID {id_empleado_recibido}. Nuevo estado: {new_status_text}")
                
                break

    def create_employee_table(self):
        self.data_file = os.path.join(BASE_DIR,"assets", "asistencia.json")
        self.employees_data = []
        try:
            with open(self.data_file, "r") as f:
                self.employees_data= json.load(f)
            print(f"✅ Datos de asistencia cargados desde {self.data_file}")
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"⚠️ No se encontró el archivo de datos o está corrupto. Creando datos por defecto.")
            self.employees_data = [
                {"id": "1", "nombre": "Enrique Mauricio Cáceres Paladino", "entrada": "-", "salida": "-", "estado": "Ausente"},
                {"id": "2", "nombre": "Leonardo Miguel Rojas Valdivia", "entrada": "-", "salida": "-", "estado": "Ausente"},
                {"id": "3", "nombre": "Justin David Escoto valle", "entrada": "-", "salida": "-", "estado": "Ausente"},
                {"id": "4", "nombre": "César Alberto Paredes Canales", "entrada": "-", "salida": "-", "estado": "Ausente"},
            ]
        table = QTableWidget()
        table.setObjectName("employee_table")
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Nombre", "Hora de Entrada", "Hora de Salida", "Estado"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # Columna Nombre
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Columna Entrada
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Columna Salida
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Columna Estado
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(44)
        table.setRowCount(len(self.employees_data))
        for row, employee_data in enumerate(self.employees_data):
            item_nombre = QTableWidgetItem(employee_data["nombre"])
            item_nombre.setData(Qt.ItemDataRole.UserRole, employee_data["id"])
            table.setItem(row, 0, item_nombre)
            table.setItem(row, 1, QTableWidgetItem(employee_data["entrada"]))
            table.setItem(row, 2, QTableWidgetItem(employee_data["salida"]))
            status_txt = employee_data["estado"]
            cell_widget = QWidget()
            h_layout = QHBoxLayout(cell_widget)
            h_layout.setContentsMargins(8, 0, 0, 0)
            h_layout.setSpacing(10)
            h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            dot = QLabel()
            dot.setObjectName("status_indicator")
            dot.setFixedSize(14, 14)
            dot.setProperty("status", "present" if status_txt.lower().startswith("pres") else "absent")
            text = QLabel(status_txt)
            text.setObjectName("status_text")
            h_layout.addWidget(dot)
            h_layout.addWidget(text)
            table.setCellWidget(row, 3, cell_widget)
        return table
    
    def save_data_to_file(self):
        if not hasattr(self, 'employees_data'):
            print("❌ Error: self.employees_data no existe. No se puede guardar.")
            return
        if not hasattr(self, 'data_file'):
            print("❌ Error: self.data_file no está definido. No se puede guardar.")
            return
        try:
            with open(self.data_file, "w", encoding='utf-8') as f:
                json.dump(self.employees_data, f, indent=4, ensure_ascii=False)
            print(f"💾 Datos de asistencia guardados en {self.data_file}")
        except IOError:
            print(f"❌ Error: No se pudo guardar el archivo de datos.")

    def limpiar_registros(self):
        """Resetea las horas en asistencia.json Y BORRA TODO el historial en asistencia_historico.json."""

        confirm = QMessageBox.question(self, "Confirmar Limpieza TOTAL",
                                    "¿Está seguro de que desea limpiar todos los registros de asistencia?\n\n"
                                    "Esto reseteará las horas en la tabla diaria Y **BORRARÁ PERMANENTEMENTE TODO EL HISTORIAL** usado para la nómina.\n\n"
                                    "¡Esta acción no se puede deshacer!", # Mensaje de advertencia más fuerte
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) # Por defecto NO
        if confirm == QMessageBox.StandardButton.No:
            return

        print("🧹🧹 Limpiando registros actuales Y TODO el historial...")

        asistencia_historico_path = os.path.join(BASE_DIR, "assets", "asistencia_historico.json")
        try:
            with open(asistencia_historico_path, "w", encoding='utf-8') as f:
                json.dump([], f, indent=4, ensure_ascii=False)
            print(f"🧹🧹 ¡TODO el historial en {asistencia_historico_path} ha sido eliminado!")

        except IOError as e:
            print(f"❌ Error al borrar el historial de asistencia: {e}")
            QMessageBox.critical(self, "Error al Borrar Historial", f"No se pudo borrar el archivo de historial:\n{e}")
            return

        if not hasattr(self, 'employee_table'):
            return
        for row in range(self.employee_table.rowCount()):
            self.employee_table.setItem(row, 1, QTableWidgetItem("-"))
            self.employee_table.setItem(row, 2, QTableWidgetItem("-"))

            widget_estado = self.employee_table.cellWidget(row, 3)
            if widget_estado:
                dot = widget_estado.findChild(QLabel, "status_indicator")
                text = widget_estado.findChild(QLabel, "status_text")
                if dot:
                    dot.setProperty("status", "absent")
                    dot.style().polish(dot)
                if text:
                    text.setText("Ausente")

            if row < len(self.employees_data):
                self.employees_data[row]["entrada"] = "-"
                self.employees_data[row]["salida"] = "-"
                self.employees_data[row]["estado"] = "Ausente"

        self.save_data_to_file()
        print("✅ Registros actuales limpiados y guardados.")
        QMessageBox.information(self,"Limpieza Completa", "Se han limpiado los registros diarios y todo el historial de asistencia.")
            

    def get_employees_data(self):
        """Devuelve los datos de los empleados cargados desde el archivo."""
        table_data = []
        try:
            if not hasattr(self, 'data_file'):
                self.data_file = os.path.join(BASE_DIR,"assets", "asistencia.json")
            with open(self.data_file, "r") as f:
                table_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ No se pudo cargar el archivo de datos para la página de Admin.")
        return table_data
    
class CocinaPage(QWidget):
    
    def load_active_orders(self):
        """Carga las órdenes activas desde el archivo JSON y las muestra."""
        self.orders_file_path = os.path.join(BASE_DIR, "assets", "cocina_ordenes.json")
        self.active_orders_data = [] 
        try:
            with open(self.orders_file_path, "r") as f:
                self.active_orders_data = json.load(f)
            print(f"🍳 Órdenes de cocina cargadas desde {self.orders_file_path}")
            for orden_data in self.active_orders_data:
                self._display_order_ticket(orden_data)
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ No se encontró archivo de órdenes de cocina o está corrupto. Iniciando vacío.")
            self.active_orders_data = []

    def save_active_orders(self):
        """Guarda la lista actual de órdenes activas en el archivo JSON."""
        try:
            with open(self.orders_file_path, "w") as f:
                json.dump(self.active_orders_data, f, indent=4)
            print(f"💾 Órdenes de cocina guardadas en {self.orders_file_path}")
        except IOError:
            print("❌ Error al guardar las órdenes de cocina.")

    def _display_order_ticket(self, orden_data):
        """Función auxiliar para crear y mostrar un ticket (evita duplicar código)."""
        nuevo_ticket = OrderTicketWidget(orden_data)
        nuevo_ticket.orden_lista.connect(self.remover_orden)
        self.ticket_container_layout.addWidget(nuevo_ticket)

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        title = QLabel("Órdenes Entrantes")
        title.setObjectName("section_title")
        main_layout.addWidget(title)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) 
        main_layout.addWidget(scroll_area)
        container_widget = QWidget()
        self.ticket_container_layout = QVBoxLayout(container_widget)
        self.ticket_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(container_widget)
        self.load_active_orders()

    def agregar_orden(self, datos_cocina):
        """Añade la orden a la lista de datos y a la vista, luego guarda."""
        print("🍳 Añadiendo nueva orden a Cocina...")
        self.active_orders_data.append(datos_cocina)
        self._display_order_ticket(datos_cocina)
        self.save_active_orders()

    def remover_orden(self, ticket_widget):
        print("✅ Orden marcada como lista. Removiendo ticket.")
        mesa_label_text = ticket_widget.findChild(QLabel, "ticket_title").text() 
        mesa_num_str = mesa_label_text.split(": ")[1]
        
        orden_a_eliminar = None
        for orden in self.active_orders_data:
            if str(orden.get("numero_mesa")) == mesa_num_str:
                orden_a_eliminar = orden
                break
        
        if orden_a_eliminar:
            self.active_orders_data.remove(orden_a_eliminar)
            self.save_active_orders()
            self.ticket_container_layout.removeWidget(ticket_widget)
            ticket_widget.deleteLater()
        else:
            print(f"⚠️ No se encontró la orden de la mesa {mesa_num_str} para eliminar en los datos guardados.")
            self.ticket_container_layout.removeWidget(ticket_widget)
            ticket_widget.deleteLater()


class CajaPage(QWidget):

    def load_active_orders(self):
        """Carga las órdenes activas desde el archivo JSON y actualiza la vista."""
        self.orders_file_path = os.path.join(BASE_DIR, "assets", "caja_ordenes.json")
        self.ordenes_activas = {} 
        self.lista_mesas.clear() 
        try:
            with open(self.orders_file_path, "r") as f:
                self.ordenes_activas = json.load(f)
            print(f"💰 Órdenes de caja cargadas desde {self.orders_file_path}")
            for mesa_num in self.ordenes_activas.keys():
                self.lista_mesas.addItem(QListWidgetItem(f"Mesa {mesa_num}"))
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ No se encontró archivo de órdenes de caja o está corrupto. Iniciando vacío.")
            self.ordenes_activas = {}

    def save_active_orders(self):
        """Guarda el diccionario actual de órdenes activas en el archivo JSON."""
        try:
            with open(self.orders_file_path, "w") as f:
                json.dump(self.ordenes_activas, f, indent=4)
            print(f"💾 Órdenes de caja guardadas en {self.orders_file_path}")
        except IOError:
            print("❌ Error al guardar las órdenes de caja.")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ordenes_activas = {}
        self.ventas_file_path = os.path.join(BASE_DIR, "assets", "ventas_completadas.json")
        main_layout = QHBoxLayout(self)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(300)
        
        mesas_title = QLabel("Mesas con Órdenes Abiertas")
        mesas_title.setObjectName("section_title")
        self.lista_mesas = QListWidget()
        self.lista_mesas.setObjectName("lista_mesas_caja")
        left_layout.addWidget(mesas_title)
        left_layout.addWidget(self.lista_mesas)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        cuenta_title = QLabel("Detalle de la Cuenta")
        cuenta_title.setObjectName("section_title")
        self.tabla_cuenta = QTableWidget()
        self.tabla_cuenta.setObjectName("tabla_cuenta_caja")
        self.tabla_cuenta.setColumnCount(4)
        self.tabla_cuenta.setHorizontalHeaderLabels(["Cantidad", "Producto", "Precio Unit.", "Subtotal"])
        self.tabla_cuenta.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.total_label = QLabel("Total: C$ 0.00")
        self.total_label.setObjectName("total_label")
        
        self.cobrar_button = QPushButton("Cobrar y Cerrar Mesa")
        self.cobrar_button.setObjectName("orange_button")
        
        right_layout.addWidget(cuenta_title)
        right_layout.addWidget(self.tabla_cuenta)
        right_layout.addWidget(self.total_label)
        right_layout.addWidget(self.cobrar_button)
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        self.lista_mesas.itemClicked.connect(self.mostrar_cuenta_de_mesa)
        self.cobrar_button.clicked.connect(self.cobrar_cuenta)
        self.load_active_orders()

    def agregar_orden(self, orden_completa):
        """Añade una nueva orden o actualiza una existente."""
        mesa_num = str(orden_completa['numero_mesa'])
        
        item_de_mesa = None
        item_es_nuevo = False

        items_en_lista = self.lista_mesas.findItems(f"Mesa {mesa_num}", Qt.MatchFlag.MatchExactly)

        if items_en_lista:
            item_de_mesa = items_en_lista[0]
            self.ordenes_activas[mesa_num]['items'].extend(orden_completa['items'])
        else:
            self.ordenes_activas[mesa_num] = orden_completa
            item_de_mesa = QListWidgetItem(f"Mesa {mesa_num}")
            # --- INICIO DE LA CORRECCIÓN ---
            self.lista_mesas.addItem(item_de_mesa) # ¡CORREGIDO! Usar la variable
            # --- FIN DE LA CORRECCIÓN ---
            item_es_nuevo = True
        
        item_actual_seleccionado = self.lista_mesas.currentItem()
        
        if item_actual_seleccionado and item_actual_seleccionado.text().split(" ")[1] == mesa_num:
            self.refrescar_vista_actual()
        elif not item_actual_seleccionado and item_es_nuevo:
            self.lista_mesas.setCurrentItem(item_de_mesa) 
            self.refrescar_vista_actual() 

        
        self.refrescar_vista_actual() 
        print(f"💰 Orden para la mesa {mesa_num} recibida/actualizada en Caja.") #
        self.save_active_orders() 

    def mostrar_cuenta_de_mesa(self, item):
        
        if not item:
            self.tabla_cuenta.setRowCount(0)
            self.total_label.setText("Total: C$ 0.00")
            return

        mesa_num = item.text().split(" ")[1]
        
        if mesa_num in self.ordenes_activas:
            orden = self.ordenes_activas[mesa_num]
            self.tabla_cuenta.setRowCount(len(orden['items']))
            
            total = 0.0
            for row, platillo in enumerate(orden['items']):
                cantidad = platillo['cantidad']
                nombre = platillo['nombre']
                precio = platillo['precio_unitario']
                subtotal = cantidad * precio
                total += subtotal
                
                self.tabla_cuenta.setItem(row, 0, QTableWidgetItem(str(cantidad)))
                self.tabla_cuenta.setItem(row, 1, QTableWidgetItem(nombre))
                self.tabla_cuenta.setItem(row, 2, QTableWidgetItem(f"C$ {precio:.2f}"))
                self.tabla_cuenta.setItem(row, 3, QTableWidgetItem(f"C$ {subtotal:.2f}"))
            self.total_label.setText(f"Total: C$ {total:.2f}")


        else:
            print(f"Error: Mesa {mesa_num} no encontrada en ordenes_activas. Limpiando vista.")
            self.tabla_cuenta.setRowCount(0)
            self.total_label.setText("Total: C$ 0.00")    

    def cobrar_cuenta(self):
        """Cierra la cuenta, la guarda como venta completada y actualiza la vista."""
        item_seleccionado = self.lista_mesas.currentItem()
        if not item_seleccionado: 
            QMessageBox.warning(self, "Acción no válida", "Por favor, seleccione una mesa para cobrar.")
            return
        
        mesa_num = item_seleccionado.text().split(" ")[1]
        
        if mesa_num in self.ordenes_activas:

            orden_a_guardar = self.ordenes_activas.pop(mesa_num)
            orden_a_guardar["fecha_cierre"] = datetime.datetime.now().isoformat()
            self.guardar_venta_completada(orden_a_guardar)
            self.save_active_orders()

            try:
                
                requests.post('http://127.0.0.1:5000/trigger_update', json={'event': 'mesas_actualizadas'})
            except requests.exceptions.RequestException as e:
                print(f"⚠️ No se pudo notificar a los clientes (trigger_update): {e}")

        self.lista_mesas.takeItem(self.lista_mesas.row(item_seleccionado))
        self.tabla_cuenta.setRowCount(0)
        self.total_label.setText("Total: C$ 0.00")
        print(f"✅ Cuenta de la mesa {mesa_num} cerrada y guardada en ventas.")

    def refrescar_vista_actual(self):
        item_actual = self.lista_mesas.currentItem()
        if item_actual:
            self.mostrar_cuenta_de_mesa(item_actual)

    def guardar_venta_completada(self, orden_completada):
        ventas_lista = []
        try:
            with open(self.ventas_file_path, "r", encoding='utf-8') as f:
                ventas_lista = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            ventas_lista = []
        ventas_lista.append(orden_completada)
        try:
            with open(self.ventas_file_path, "w", encoding='utf-8') as f:
                json.dump(ventas_lista, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"❌ Error al guardar venta completada: {e}")    

def QSpacerItem(arg1, arg2, arg3, arg4):
    raise NotImplementedError

class AdminPage(QWidget):
    employees_updated = pyqtSignal(list)
    config_updated = pyqtSignal(dict)

    def __init__(self, employees_data, initial_config, parent=None):
        super().__init__(parent)
        self.employees_data = employees_data
        self.current_config = initial_config
        self.menu_file_path = os.path.join(BASE_DIR, "assets", "menu.json")
        self.ventas_file_path = os.path.join(BASE_DIR, "assets", "ventas_completadas.json")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 25)
        main_layout.setSpacing(15)

        title = QLabel("Panel de Administración")
        title.setObjectName("section_title")

        main_layout.addWidget(title)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        employee_tab = QWidget()
        employee_layout = QVBoxLayout(employee_tab)
        employee_layout.setContentsMargins(15, 15, 15, 15)
        employee_layout.setSpacing(15)
        employee_controls_layout = QHBoxLayout()

        self.btn_add_employee = QPushButton("Añadir Empleado")
        self.btn_add_employee.setObjectName("orange_button")
        self.btn_edit_employee = QPushButton("Editar Empleado")
        self.btn_edit_employee.setObjectName("orange_button")
        self.btn_delete_employee = QPushButton("Eliminar Empleado")
        self.btn_delete_employee.setObjectName("orange_button")

        employee_controls_layout.addWidget(self.btn_add_employee)
        employee_controls_layout.addWidget(self.btn_edit_employee)
        employee_controls_layout.addWidget(self.btn_delete_employee)
        employee_controls_layout.addStretch()
        employee_layout.addLayout(employee_controls_layout)

        self.employee_table = QTableWidget()
        self.employee_table.setObjectName("employee_table")
        self.employee_table.setColumnCount(3) 
        self.employee_table.setHorizontalHeaderLabels(["ID", "Nombre Completo", "Rol"]) 

        header = self.employee_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed) # Columna Rol

        self.employee_table.setColumnWidth(0, 150)
        self.employee_table.setColumnWidth(2, 150) # Ancho para Rol
        employee_layout.addWidget(self.employee_table)
        self.tab_widget.addTab(employee_tab, "Empleados")

        self.available_roles = []
        try:
            config_path = os.path.join(BASE_DIR, "assets", "config.json")
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                self.available_roles = list(config_data.get("roles_pago", {}).keys())
                if not self.available_roles:
                    print("⚠️ No se encontraron roles en config.json. Usando lista por defecto.")
                    self.available_roles = ["Mesero", "Cajera", "Jefe de Cocina", "Michelero"]
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ No se encontró config.json. Usando lista de roles por defecto.")
            self.available_roles = ["Mesero", "Cajera", "Jefe de Cocina", "Michelero"]


        tables_tab = QWidget()
        tables_layout = QVBoxLayout(tables_tab)
        tables_layout.setContentsMargins(15, 15, 15, 15)
        tables_layout.setSpacing(15)
        table_controls_layout = QHBoxLayout()
        table_controls_layout.addWidget(QLabel("Gestionar Mesas:"))

        self.btn_add_table = QPushButton("(+) Añadir Mesa")
        self.btn_add_table.setObjectName("orange_button")
        self.btn_remove_table = QPushButton("(-) Quitar Mesa")
        self.btn_remove_table.setObjectName("orange_button")

        table_controls_layout.addWidget(self.btn_add_table)
        table_controls_layout.addWidget(self.btn_remove_table)
        table_controls_layout.addStretch()
        tables_layout.addLayout(table_controls_layout)

        scroll_area_tables = QScrollArea()
        scroll_area_tables.setWidgetResizable(True)

        tables_layout.addWidget(scroll_area_tables)
        self.table_cards_container = QWidget()
        self.table_cards_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.table_grid_layout = QGridLayout(self.table_cards_container)
        self.table_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.table_grid_layout.setSpacing(20)
        cols = 5
        for col in range(cols):
            self.table_grid_layout.setColumnStretch(col, 1)
        scroll_area_tables.setWidget(self.table_cards_container)
        self.tab_widget.addTab(tables_tab, "Mesas")
        menu_tab = QWidget()
        menu_layout = QVBoxLayout(menu_tab)
        menu_layout.setContentsMargins(15, 15, 15, 15)
        menu_layout.setSpacing(15)
        # Botón para guardar cambios en el menú
        self.btn_save_menu = QPushButton("Guardar Estado del Menú")
        self.btn_save_menu.setObjectName("orange_button")
        
        menu_layout.addWidget(self.btn_save_menu)
        # Árbol para mostrar el menú jerárquico
        self.menu_tree = QTreeWidget()
        self.menu_tree.setObjectName("menu_tree")
        self.menu_tree.setColumnCount(1) # <-- CAMBIO: Solo 1 columna
        self.menu_tree.setHeaderLabels(["Platillo / Categoría"])
        # Ajustes de estilo para mejorar la apariencia
        menu_header = self.menu_tree.header()
        menu_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.menu_tree.setStyleSheet("QTreeWidget::item { height: 60px; }") 
        # Agrega el árbol al layout
        menu_layout.addWidget(self.menu_tree)
        self.tab_widget.addTab(menu_tab, "Gestión de Menú")
        # Pestaña de Reportes
        reportes_tab = QWidget()
        reportes_layout = QHBoxLayout(reportes_tab) # Layout horizontal
        reportes_tab.setLayout(reportes_layout)
        reportes_layout.setContentsMargins(15, 15, 15, 15)
        # Espacio izquierdo para el calendario
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(400) # Tamaño fijo para el calendario
        # Añade el calendario
        left_layout.addWidget(QLabel("Seleccione un día:"))
        self.calendar = QCalendarWidget()
        self.calendar.setObjectName("report_calendar")
        left_layout.addWidget(self.calendar)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.report_total_label = QLabel("Total de Ventas: C$ 0.00")
        self.report_total_label.setObjectName("section_title") # Reutilizamos el estilo
        
        right_layout.addWidget(QLabel("Platillos más vendidos de ese día:"))
        self.report_table = QTableWidget()
        self.report_table.setObjectName("employee_table") # Reutilizamos el estilo
        self.report_table.setColumnCount(2)
        self.report_table.setHorizontalHeaderLabels(["Platillo", "Cantidad Vendida"])
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.report_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.report_table.setColumnWidth(1, 150)
        # Añade los widgets al layout derecho
        right_layout.addWidget(self.report_total_label)
        right_layout.addWidget(self.report_table)
        reportes_layout.addWidget(left_panel)
        reportes_layout.addWidget(right_panel)
        self.tab_widget.addTab(reportes_tab, "Reportes")


        payroll_tab = QWidget()
        payroll_layout = QVBoxLayout(payroll_tab) # Layout vertical principal
        payroll_tab.setLayout(payroll_layout)
        payroll_layout.setContentsMargins(15, 15, 15, 15)
        payroll_layout.setSpacing(15)

        controls_hbox = QHBoxLayout()
        payroll_layout.addLayout(controls_hbox)

        # Selectores de Fecha
        controls_hbox.addWidget(QLabel("Desde:"))
        self.payroll_start_date = QDateEdit()
        self.payroll_start_date.setCalendarPopup(True)
        self.payroll_start_date.setDate(QDate.currentDate().addMonths(-1)) # Por defecto, un mes atrás
        controls_hbox.addWidget(self.payroll_start_date)

        controls_hbox.addWidget(QLabel("Hasta:"))
        self.payroll_end_date = QDateEdit()
        self.payroll_end_date.setCalendarPopup(True)
        self.payroll_end_date.setDate(QDate.currentDate()) # Por defecto, hoy
        controls_hbox.addWidget(self.payroll_end_date)

        # Botón Calcular
        self.btn_calculate_payroll = QPushButton("Calcular Nómina")
        self.btn_calculate_payroll.setObjectName("orange_button")
        controls_hbox.addWidget(self.btn_calculate_payroll)

        controls_hbox.addStretch() # Empuja todo a la izquierda

        self.btn_export_pdf = QPushButton("Exportar PDF Seleccionado")
        self.btn_export_pdf.setObjectName("orange_button")
        self.btn_export_pdf.setEnabled(False) # Empieza deshabilitado
        controls_hbox.addWidget(self.btn_export_pdf)
        

        self.btn_generate_random = QPushButton("Generar Datos Aleatorios (Test)")
        controls_hbox.addWidget(self.btn_generate_random)


        
        payroll_layout.addWidget(QLabel("Resultados de Nómina:"))
        self.payroll_table = QTableWidget()
        self.payroll_table.setObjectName("employee_table") # Reutilizamos estilo
        self.payroll_table.setColumnCount(7) # 7 columnas
        self.payroll_table.setHorizontalHeaderLabels([
            "Empleado", "Rol", "Hrs Reg.", "Hrs Ext.",
            "Pago Reg. (C$)", "Pago Ext. (C$)", "Pago Total (C$)"
        ])
        payroll_header = self.payroll_table.horizontalHeader()
        payroll_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # Nombre
        payroll_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Rol
        payroll_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Hrs Reg
        payroll_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Hrs Ext
        payroll_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # Pago Reg
        payroll_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch) # Pago Ext
        payroll_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch) # Pago Total
        
        
        self.payroll_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.payroll_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        payroll_layout.addWidget(self.payroll_table)

        self.tab_widget.addTab(payroll_tab, "Nómina")
        # Fin pestaña 5

        self.load_table_data()
        self.populate_table_cards()  # Llena la cuadrícula de mesas
        self.load_menu_data()     # Llena la tabla de menú
        self.btn_add_employee.clicked.connect(self.add_employee)
        self.btn_edit_employee.clicked.connect(self.edit_employee)
        self.btn_delete_employee.clicked.connect(self.delete_employee)
        self.btn_add_table.clicked.connect(self.add_table)  # Conecta nuevo botón
        self.btn_remove_table.clicked.connect(self.remove_table)  # Conecta nuevo botón
        self.btn_save_menu.clicked.connect(self.save_menu_data)  # Conecta botón de guardar menú
        self.calendar.selectionChanged.connect(self.mostrar_reporte_del_dia)
        self.mostrar_reporte_del_dia()

        self.btn_calculate_payroll.clicked.connect(self.calculate_payroll)
        self.btn_export_pdf.clicked.connect(self.export_payroll_pdf)
        self.btn_generate_random.clicked.connect(self.generate_random_attendance)
        
        self.payroll_table.itemSelectionChanged.connect(self.update_export_button_state)

    def populate_table_cards(self):
        """Limpia y vuelve a crear las tarjetas de mesa en la cuadrícula."""
        while self.table_grid_layout.count():
            item = self.table_grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        total_mesas = self.current_config.get("total_mesas", 10)
        cols = 5  # Número de columnas deseadas en la cuadrícula
        for i in range(total_mesas):
            table_number = i + 1
            card = TableCardWidget(table_number)
            row = i // cols
            col = i % cols
            self.table_grid_layout.addWidget(card, row, col)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_grid_layout.addWidget(spacer, self.table_grid_layout.rowCount(), 0, 1, -1)
        self.btn_remove_table.setEnabled(total_mesas > 1)

    def add_table(self):
        """Incrementa el número de mesas y refresca la vista."""
        current_total = self.current_config.get("total_mesas", 10)
        if current_total < 100:
            self.current_config["total_mesas"] = current_total + 1
            self.populate_table_cards()  # Redibuja las tarjetas
            self.config_updated.emit(self.current_config)  # Notifica a MainWindow
            print(f"⚙️ Mesa añadida. Total: {self.current_config['total_mesas']}")
        else:
            QMessageBox.information(self, "Límite Alcanzado", "Se ha alcanzado el número máximo de mesas (100).")

    def remove_table(self):
        """Decrementa el número de mesas y refresca la vista."""
        current_total = self.current_config.get("total_mesas", 10)
        if current_total > 1:  # Asegura que siempre quede al menos 1 mesa
            self.current_config["total_mesas"] = current_total - 1
            self.populate_table_cards()  # Redibuja las tarjetas
            self.config_updated.emit(self.current_config)  # Notifica a MainWindow
            print(f"⚙️ Mesa eliminada. Total: {self.current_config['total_mesas']}")
        else:
            QMessageBox.warning(self, "Acción no permitida", "Debe haber al menos una mesa.")

    def load_table_data(self):
        """Limpia y vuelve a llenar la tabla con los datos de los empleados."""
        self.employee_table.setRowCount(0)
        self.employee_table.setRowCount(len(self.employees_data))
        for row, employee in enumerate(self.employees_data):
            id_item = QTableWidgetItem(employee.get("id"))
            name_item = QTableWidgetItem(employee.get("nombre"))
            rol_item = QTableWidgetItem(employee.get("rol", "No asignado"))

            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            rol_item.setFlags(rol_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.employee_table.setItem(row, 0, id_item)
            self.employee_table.setItem(row, 1, name_item)
            self.employee_table.setItem(row, 2, rol_item)

    def delete_employee(self):
        """Elimina el empleado seleccionado de la tabla y de la lista de datos."""
        
        current_row = self.employee_table.currentRow()
        
        if current_row < 0:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, seleccione un empleado de la tabla para eliminar.")
            return
        id_item = self.employee_table.item(current_row, 0)
        name_item = self.employee_table.item(current_row, 1)
        employee_id = id_item.text()
        employee_name = name_item.text()
        confirm = QMessageBox.question(self, "Confirmar Eliminación", 
                                    f"¿Está seguro de que desea eliminar a '{employee_name}' (ID: {employee_id})?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.employees_data[:] = [emp for emp in self.employees_data if emp.get("id") != employee_id]
            self.load_table_data()
            
            print(f"✅ Empleado '{employee_name}' (ID: {employee_id}) eliminado.")
            self.employees_updated.emit(self.employees_data)
        else:
            print("Operación cancelada.")

    def add_employee(self):
        """Muestra diálogos para añadir un nuevo empleado."""
        
        new_id, ok1 = QInputDialog.getText(self, 'Añadir Empleado', 'Ingrese el ID del nuevo empleado:')
        
        if not ok1 or not new_id.strip():
            print("Operación cancelada.")
            return
        new_id = new_id.strip() # Limpiamos espacios
        for employee in self.employees_data:
            if employee.get("id") == new_id:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", f"El ID '{new_id}' ya existe.")
                return
        new_name, ok2 = QInputDialog.getText(self, 'Añadir Empleado', 'Ingrese el nombre completo del nuevo empleado:')
        if not ok2 or not new_name.strip():
            print("Operación cancelada (Nombre).")
            return

        new_rol, ok3 = QInputDialog.getItem(self, "Añadir Empleado", "Seleccione el rol:", self.available_roles, 0, False)
        if not ok3 or not new_rol:
            print("Operación cancelada (Rol).")
            return
        new_name = new_name.strip()
        new_employee_data = {
            "id": new_id,
            "nombre": new_name,
            "entrada": "-",
            "salida": "-",
            "estado": "Ausente",
            "deviceId": None, 
            "rol": new_rol
        }
        self.employees_data.append(new_employee_data)
        self.load_table_data()
        
        print(f"✅ Empleado '{new_name}' (ID: {new_id}) añadido.")
        self.employees_updated.emit(self.employees_data)

    def edit_employee(self):
        current_row = self.employee_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione un empleado para editar.")
            return
        
        original_employee = self.employees_data[current_row]
        original_id = original_employee.get("id", "")
        original_name = original_employee.get("nombre", "")
        original_rol = original_employee.get("rol", "")

        new_id, ok1 = QInputDialog.getText(self, 'Editar Empleado', 'ID:', QLineEdit.EchoMode.Normal, original_id)
        if not ok1 or not new_id.strip(): return
        new_id = new_id.strip()
        if not new_id:
            QMessageBox.warning(self, "Error", "El ID no puede estar vacío.")
            return
        if any(emp.get("id") == new_id for i, emp in enumerate(self.employees_data) if i != current_row):
            QMessageBox.warning(self, "Error", f"El ID '{new_id}' ya está en uso.")
            return

        new_name, ok2 = QInputDialog.getText(self, 'Editar Empleado', 'Nombre Completo:', QLineEdit.EchoMode.Normal, original_name)
        if not ok2 or not new_name.strip(): return
        new_name = new_name.strip()

        try:
            current_role_index = self.available_roles.index(original_rol)
        except ValueError:
            current_role_index = 0 

        new_rol, ok3 = QInputDialog.getItem(self, "Editar Empleado", "Seleccione el rol:", self.available_roles, current_role_index, False)
        if not ok3 or not new_rol:
            print("Edición cancelada (Rol).")
            return

        self.employees_data[current_row]["id"] = new_id
        self.employees_data[current_row]["nombre"] = new_name
        self.employees_data[current_row]["rol"] = new_rol 

        self.load_table_data() # Refrescar la tabla visual
        
        print(f"✅ Empleado (ID original: {original_id}) actualizado a ID: {new_id}, Nombre: {new_name}, Rol: {new_rol}.")
        self.employees_updated.emit(self.employees_data) # Notificar cambios

    def load_menu_data(self):
        """Carga el menu.json y lo muestra en el QTreeWidget usando widgets personalizados."""
        self.menu_tree.clear() 
        
        try:
            with open(self.menu_file_path, "r", encoding='utf-8') as f:
                menu_data = json.load(f)
            for categoria_data in menu_data.get("categorias", []):
                categoria_nombre = categoria_data.get("nombre", "Sin Categoría")
                parent_item = QTreeWidgetItem(self.menu_tree)
                parent_item.setText(0, categoria_nombre)
                parent_item.setData(0, Qt.ItemDataRole.UserRole, "categoria")
                parent_item.setFlags(parent_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                for item_data in categoria_data.get("items", []):
                    child_item = QTreeWidgetItem(parent_item)
                    
                    platillo_widget = PlatilloItemWidget(item_data)
                    
                    self.menu_tree.setItemWidget(child_item, 0, platillo_widget)
            self.menu_tree.expandAll()
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"❌ Error: No se pudo cargar el archivo {self.menu_file_path}.")
            QMessageBox.critical(self, "Error de Menú", "No se pudo cargar el archivo 'menu.json'. Verifica que exista en la carpeta 'assets'.")
        except Exception as e:
            print(f"❌ Error inesperado al cargar menú: {e}")

    def save_menu_data(self):
        """Lee el estado de todos los PlatilloItemWidget y sobrescribe el menu.json."""
        menu_data = {}
        try:
            with open(self.menu_file_path, "r", encoding='utf-8') as f:
                menu_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            QMessageBox.critical(self, "Error al Guardar", "No se pudo leer el 'menu.json' original para guardar.")
            return
        updates = {}
        iterator = QTreeWidgetItemIterator(self.menu_tree)
        
        while iterator.value():
            item = iterator.value()
            widget = self.menu_tree.itemWidget(item, 0)
            if isinstance(widget, PlatilloItemWidget):
                updates[widget.item_id] = widget.disponible
            
            iterator += 1
        for categoria in menu_data.get("categorias", []):
            for item in categoria.get("items", []):
                item_id = item.get("id") 
                if item_id in updates:
                    item["disponible"] = updates[item_id]
        try:
            with open(self.menu_file_path, "w", encoding='utf-8') as f:
                json.dump(menu_data, f, indent=4, ensure_ascii=False)
            
            print(f"💾 Menú guardado exitosamente en {self.menu_file_path}")
            QMessageBox.information(self, "Éxito", "El estado del menú se ha guardado correctamente.")

            try:
                    requests.post('http://127.0.0.1:5000/trigger_update', json={'event': 'menu_actualizado'})
            except requests.exceptions.RequestException as e:
                    print(f"⚠️ No se pudo notificar a los clientes (trigger_update): {e}")

        except IOError:
            print(f"❌ Error: No se pudo escribir en {self.menu_file_path}")
            QMessageBox.critical(self, "Error al Guardar", "No se pudo escribir en el archivo 'menu.json'.")

    def mostrar_reporte_del_dia(self):
        """Lee el archivo de ventas y genera el reporte para el día seleccionado."""
        
        selected_date = self.calendar.selectedDate().toPyDate()
        selected_date_str = selected_date.isoformat() # Ej: "2025-10-27"
        
        all_ventas = []
        try:
            with open(self.ventas_file_path, "r", encoding='utf-8') as f:
                all_ventas = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            all_ventas = [] 
        ventas_del_dia = []
        for orden in all_ventas:
            fecha_cierre_str = orden.get("fecha_cierre", "")
            if fecha_cierre_str.startswith(selected_date_str):
                ventas_del_dia.append(orden)
        
        
        total_ventas = 0.0
        items_vendidos = {} 
        for orden in ventas_del_dia:
            for item in orden.get("items", []):
                total_ventas += item.get("cantidad", 0) * item.get("precio_unitario", 0)
                item_id = item.get("item_id")
                if item_id:
                    if item_id not in items_vendidos:
                        items_vendidos[item_id] = {
                            "nombre": item.get("nombre", "Desconocido"),
                            "cantidad": 0
                        }
                    items_vendidos[item_id]["cantidad"] += item.get("cantidad", 0)
        self.report_total_label.setText(f"Total de Ventas: C$ {total_ventas:.2f}")
        sorted_items = sorted(items_vendidos.values(), key=lambda x: x["cantidad"], reverse=True)
        self.report_table.setRowCount(len(sorted_items))
        for row, item in enumerate(sorted_items):
            item_nombre = QTableWidgetItem(item["nombre"])
            item_cantidad = QTableWidgetItem(str(item["cantidad"]))
            item_cantidad.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.report_table.setItem(row, 0, item_nombre)
            self.report_table.setItem(row, 1, item_cantidad)
            
        print(f"📊 Reporte generado para {selected_date_str}. Total: C${total_ventas:.2f}")

    def calculate_payroll(self):
        """Calcula la nómina, muestra totales y guarda detalles diarios para PDF."""
        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()

        start_date = start_date_q.toPyDate()
        end_date_inclusive = end_date_q.toPyDate()
        end_date_exclusive = end_date_q.toPyDate() + datetime.timedelta(days=1)

        print(f"💰 Calculando nómina desde {start_date} hasta {end_date_inclusive}...")

        # 1. Cargar datos necesarios
        payroll_rates = self.current_config.get("roles_pago", {})
        if not payroll_rates:
            QMessageBox.critical(self, "Error de Configuración", "No se encontraron tarifas de pago.")
            return

        employees_dict = {emp['id']: emp for emp in self.employees_data}

        attendance_history = []
        asistencia_historico_path = os.path.join(BASE_DIR, "assets", "asistencia_historico.json")
        try:
            with open(asistencia_historico_path, "r", encoding='utf-8') as f:
                attendance_history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ No se encontró historial de asistencia.")

        payroll_results = {}
        self.payroll_daily_details = {}

        valid_entries = []
        for entry in attendance_history:
            try:
                ts = datetime.datetime.fromisoformat(entry['timestamp'])
                if start_date <= ts.date() < end_date_exclusive:
                    valid_entries.append({
                        "employee_id": entry['employee_id'], "timestamp": ts, "type": entry['type']
                    })
            except (ValueError, KeyError): continue
            
        valid_entries.sort(key=lambda x: (x['employee_id'], x['timestamp']))

        last_entry_time = None

        for entry in valid_entries:
            emp_id = entry['employee_id']
            ts = entry['timestamp']
            entry_type = entry['type']
            day_str = ts.date().isoformat()

            if emp_id not in payroll_results:
                payroll_results[emp_id] = {"total_reg_mins": 0, "total_ot_mins": 0, "total_pay": 0.0, "total_reg_pay": 0.0, "total_ot_pay": 0.0}
            if emp_id not in self.payroll_daily_details:
                self.payroll_daily_details[emp_id] = {}
            if day_str not in self.payroll_daily_details[emp_id]:
                self.payroll_daily_details[emp_id][day_str] = {"first_entry": None, "last_exit": None, "reg_mins": 0, "ot_mins": 0, "pay": 0.0}


            if entry_type == "entrada":
                if self.payroll_daily_details[emp_id][day_str]["first_entry"] is None:
                    self.payroll_daily_details[emp_id][day_str]["first_entry"] = ts
                last_entry_time = ts # Guardamos la hora REAL de entrada

            elif entry_type == "salida" and last_entry_time is not None and last_entry_time.date() == ts.date():

                jornada_start_time = last_entry_time.replace(hour=12, minute=0, second=0, microsecond=0)

                start_time_for_calc = max(last_entry_time, jornada_start_time)
                if ts > start_time_for_calc: # Asegurarse que la salida es después del inicio calculado
                    duration = ts - start_time_for_calc
                    total_minutes_shift = duration.total_seconds() / 60
                else:
                    total_minutes_shift = 0 # No hay tiempo pagable si sale antes de las 12 PM

                employee_info = employees_dict.get(emp_id)
                rol = employee_info.get("rol") if employee_info else None
                rate_info = payroll_rates.get(rol) if rol else None

                if rate_info and "minuto" in rate_info and total_minutes_shift > 0:
                    rate_per_minute = rate_info["minuto"]

                    overtime_start_time = start_time_for_calc.replace(hour=22, minute=0, second=0, microsecond=0)
                    regular_minutes_shift = 0
                    overtime_minutes_shift = 0

                    if ts <= overtime_start_time:
                        regular_minutes_shift = total_minutes_shift
                    elif start_time_for_calc < overtime_start_time < ts:
                        regular_duration = overtime_start_time - start_time_for_calc
                        regular_minutes_shift = regular_duration.total_seconds() / 60
                        overtime_duration = ts - overtime_start_time
                        overtime_minutes_shift = overtime_duration.total_seconds() / 60
                    else: # start_time_for_calc >= overtime_start_time
                        overtime_minutes_shift = total_minutes_shift

                    # Calcular pago del turno
                    reg_pay_shift = regular_minutes_shift * rate_per_minute
                    ot_pay_shift = overtime_minutes_shift * rate_per_minute * 2
                    shift_pay = reg_pay_shift + ot_pay_shift

                    payroll_results[emp_id]["total_reg_mins"] += regular_minutes_shift
                    payroll_results[emp_id]["total_ot_mins"] += overtime_minutes_shift
                    payroll_results[emp_id]["total_reg_pay"] += reg_pay_shift 
                    payroll_results[emp_id]["total_ot_pay"] += ot_pay_shift   
                    payroll_results[emp_id]["total_pay"] += shift_pay       

                    self.payroll_daily_details[emp_id][day_str]["reg_mins"] += regular_minutes_shift
                    self.payroll_daily_details[emp_id][day_str]["ot_mins"] += overtime_minutes_shift
                    self.payroll_daily_details[emp_id][day_str]["pay"] += shift_pay
                    self.payroll_daily_details[emp_id][day_str]["last_exit"] = ts 

                    last_entry_time = None # Resetear entrada
                else: # Si no hay tarifa, rol o no hubo tiempo pagable
                    if total_minutes_shift <= 0:
                        print(f"Info: No se calculó tiempo pagable para {emp_id} el {day_str} (salida antes/igual a 12PM).")
                    else:
                        print(f"Advertencia: No se pudo calcular pago para {emp_id} el {day_str} (rol '{rol}' o tarifa inválida).")
                    self.payroll_daily_details[emp_id][day_str]["last_exit"] = ts # Guardar salida aunque no haya pago
                    last_entry_time = None

            elif last_entry_time is not None and last_entry_time.date() != ts.date():
                last_entry_time = None
                if entry_type == "entrada": # Si el nuevo día empieza con entrada, procesarlo
                    if day_str not in self.payroll_daily_details[emp_id]: # Asegurar inicialización día
                        self.payroll_daily_details[emp_id][day_str] = {"first_entry": None, "last_exit": None, "reg_mins": 0, "ot_mins": 0, "pay": 0.0}
                    if self.payroll_daily_details[emp_id][day_str]["first_entry"] is None:
                        self.payroll_daily_details[emp_id][day_str]["first_entry"] = ts
                    last_entry_time = ts


        self.payroll_table.setRowCount(0)
        self.payroll_table.setRowCount(len(payroll_results))

        row = 0
        for emp_id, results in payroll_results.items():

            employee_info = employees_dict.get(emp_id)
            if not employee_info: continue

            reg_hours = int(results["total_reg_mins"] // 60)
            reg_mins = int(results["total_reg_mins"] % 60)
            ot_hours = int(results["total_ot_mins"] // 60)
            ot_mins = int(results["total_ot_mins"] % 60)

            item_name = QTableWidgetItem(employee_info.get("nombre", "Desconocido"))
            item_rol = QTableWidgetItem(employee_info.get("rol", "N/A"))
            item_hrs_reg = QTableWidgetItem(f"{reg_hours:02d}:{reg_mins:02d}")
            item_hrs_ot = QTableWidgetItem(f"{ot_hours:02d}:{ot_mins:02d}")
            item_pay_reg = QTableWidgetItem(f"C$ {results['total_reg_pay']:.2f}") # Usar total_reg_pay
            item_pay_ot = QTableWidgetItem(f"C$ {results['total_ot_pay']:.2f}")   # Usar total_ot_pay
            item_pay_total = QTableWidgetItem(f"C$ {results['total_pay']:.2f}")

            item_name.setData(Qt.ItemDataRole.UserRole, emp_id)

            item_hrs_reg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_hrs_ot.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_pay_reg.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pay_ot.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pay_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.payroll_table.setItem(row, 0, item_name)
            self.payroll_table.setItem(row, 1, item_rol)
            self.payroll_table.setItem(row, 2, item_hrs_reg)
            self.payroll_table.setItem(row, 3, item_hrs_ot)
            self.payroll_table.setItem(row, 4, item_pay_reg)
            self.payroll_table.setItem(row, 5, item_pay_ot)
            self.payroll_table.setItem(row, 6, item_pay_total)

            row += 1
        self.update_export_button_state()
        print(f"✅ Nómina calculada y mostrada para {len(payroll_results)} empleados. Detalles diarios guardados para PDF.")


    def export_payroll_pdf(self):
        """Exporta el detalle de nómina del empleado seleccionado a PDF."""
        selected_rows = self.payroll_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione un empleado de la tabla para exportar.")
            return
            
        selected_row_index = selected_rows[0].row()
        
        employee_name_item = self.payroll_table.item(selected_row_index, 0)
        employee_rol_item = self.payroll_table.item(selected_row_index, 1)
        
        if not employee_name_item or not employee_rol_item:
            QMessageBox.warning(self, "Error", "No se pudo obtener la información del empleado seleccionado.")
            return

        employee_name = employee_name_item.text()
        employee_rol = employee_rol_item.text()
        employee_id = employee_name_item.data(Qt.ItemDataRole.UserRole) 

        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()
        start_date = start_date_q.toPyDate()
        end_date = end_date_q.toPyDate() 

        print(f"📄 Preparando PDF para {employee_name} (ID: {employee_id}) del {start_date} al {end_date}...")

        employee_daily_details = self.payroll_daily_details.get(employee_id, {})

        if not employee_daily_details:
            QMessageBox.information(self, "Sin Datos", ...)
            return

        if not employee_daily_details:
            QMessageBox.information(self, "Sin Datos", f"No se encontraron registros de asistencia calculados para {employee_name} en el período seleccionado.")
            return

        default_filename = f"Nomina_{employee_name.replace(' ', '_')}_{start_date}_a_{end_date}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", default_filename, "PDF Files (*.pdf)")

        if not save_path:
            print("Exportación cancelada por el usuario.")
            return

        try:
            pdf = FPDF()
            pdf.add_page()
            
            logo_path = os.path.join(BASE_DIR,"Assets","logopdf.png") 
            if os.path.exists(logo_path):
                pdf.image(logo_path, x=5, y=5, w=50) 
                pdf.ln(20) 
            else:
                print(f"⚠️ Advertencia: No se encontró el logo en {logo_path}")
                pdf.ln(20) 

            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Reporte de Nómina", 0, 1, 'C')
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 7, f"Empleado: {employee_name}", 0, 1)
            pdf.cell(0, 7, f"Rol: {employee_rol}", 0, 1)
            pdf.cell(0, 7, f"Período: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}", 0, 1)
            pdf.ln(10)

            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(230, 230, 230) 
            col_widths = [25, 30, 30, 30, 30, 45] 
            headers = ["Fecha", "Entrada", "Salida", "Hrs Reg.", "Hrs Ext.", "Pago Diario (C$)"] 
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, header, 1, 0, 'C', fill=True)
            pdf.ln()

            pdf.set_font("Arial", size=10)
            total_period_reg_mins = 0
            total_period_ot_mins = 0
            total_period_pay = 0.0
            
            sorted_days = sorted(employee_daily_details.keys()) 

            for day_str in sorted_days:
                details = employee_daily_details[day_str] 
                
                fecha = datetime.date.fromisoformat(day_str).strftime('%d/%m/%y')
                entrada = details['first_entry'].strftime('%I:%M %p') if details['first_entry'] else "-"
                salida = details['last_exit'].strftime('%I:%M %p') if details['last_exit'] else "-"

                reg_h = int(details["reg_mins"] // 60)
                reg_m = int(details["reg_mins"] % 60)
                hrs_reg = f"{reg_h:02d}:{reg_m:02d}" if details['reg_mins'] > 0 or details['ot_mins'] > 0 else "-"

                ot_h = int(details["ot_mins"] // 60)
                ot_m = int(details["ot_mins"] % 60)
                hrs_ot = f"{ot_h:02d}:{ot_m:02d}" if details['ot_mins'] > 0 else "00:00"

                pago_diario = f"{details['pay']:.2f}" if details['reg_mins'] > 0 or details['ot_mins'] > 0 else "-"

                pdf.cell(col_widths[0], 7, fecha, 1, 0, 'C')
                pdf.cell(col_widths[1], 7, entrada, 1, 0, 'C')
                pdf.cell(col_widths[2], 7, salida, 1, 0, 'C')
                pdf.cell(col_widths[3], 7, hrs_reg, 1, 0, 'C')
                pdf.cell(col_widths[4], 7, hrs_ot, 1, 0, 'C')
                pdf.cell(col_widths[5], 7, pago_diario, 1, 0, 'R') 
                pdf.ln()

                if details['reg_mins'] > 0 or details['ot_mins'] > 0: 
                    total_period_reg_mins += details["reg_mins"]
                    total_period_ot_mins += details["ot_mins"]
                    total_period_pay += details["pay"]

            pdf.set_font("Arial", 'B', 10)
            pdf.cell(col_widths[0] + col_widths[1] + col_widths[2], 8, "TOTALES:", 1, 0, 'R', fill=True)
            
            total_reg_h = int(total_period_reg_mins // 60)
            total_reg_m = int(total_period_reg_mins % 60)
            total_ot_h = int(total_period_ot_mins // 60)
            total_ot_m = int(total_period_ot_mins % 60)
            
            pdf.cell(col_widths[3], 8, f"{total_reg_h:02d}:{total_reg_m:02d}", 1, 0, 'C', fill=True) 
            pdf.cell(col_widths[4], 8, f"{total_ot_h:02d}:{total_ot_m:02d}", 1, 0, 'C', fill=True) 
            pdf.cell(col_widths[5], 8, f"C$ {total_period_pay:.2f}", 1, 0, 'R', fill=True) 
            pdf.ln(15)

            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Pago Total del Período: C$ {total_period_pay:.2f}", 0, 1)

            pdf.output(save_path, "F")
            print(f"✅ PDF guardado exitosamente en: {save_path}")
            QMessageBox.information(self, "Éxito", f"El reporte PDF para {employee_name} se ha guardado correctamente.")

        except Exception as e:
            print(f"❌ Error al generar el PDF: {e}")
            QMessageBox.critical(self, "Error de PDF", f"Ocurrió un error al generar el archivo PDF:\n{e}")


    def generate_random_attendance(self):
        """Genera datos de asistencia aleatorios en asistencia_historico.json para pruebas."""
        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()
        
        
        start_date = start_date_q.toPyDate()
        end_date = end_date_q.toPyDate()

        
        if start_date > end_date:
            QMessageBox.warning(self, "Fechas Inválidas", "La fecha de inicio no puede ser posterior a la fecha de fin.")
            return
            
        print(f"🎲 Preparando para generar datos aleatorios desde {start_date} hasta {end_date}...")

        
        confirm = QMessageBox.warning(self, "Confirmar Generación de Datos", 
                                    "Esto añadirá registros de entrada/salida aleatorios al archivo 'asistencia_historico.json' "
                                    "para el período seleccionado. Esto es útil para probar la nómina.\n\n"
                                    "NO afectará el estado actual mostrado en la pestaña 'Control de Asistencia'.\n\n"
                                    "¿Está seguro de que desea continuar?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) # Por defecto NO
        
        if confirm == QMessageBox.StandardButton.No:
            print("Operación cancelada.")
            return

        if not self.employees_data:
            QMessageBox.critical(self, "Error", "No se pudieron cargar los datos de empleados.")
            return
            
        asistencia_historico_path = os.path.join(BASE_DIR, "assets", "asistencia_historico.json")
        history = []
        try:
            with open(asistencia_historico_path, "r", encoding='utf-8') as f:
                history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            history = [] 

        new_entries = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5: # De Lunes a Viernes
                for employee in self.employees_data:
                    emp_id = employee.get("id")
                    if not emp_id: continue
                    
                    if random.random() < 0.9: 
                        try:
                            entry_hour = 12
                            entry_minute = random.randint(-15, 15)
                            entry_time = datetime.datetime(current_date.year, current_date.month, current_date.day, 
                                                        entry_hour, 0, 0) + datetime.timedelta(minutes=entry_minute)
                            
                            exit_hour = 22 # Centrado a las 10 PM
                            exit_minute = random.randint(-15, 60) # -15 min a +60 min
                            exit_time = datetime.datetime(current_date.year, current_date.month, current_date.day,
                                                        exit_hour, 0, 0) + datetime.timedelta(minutes=exit_minute)

                            if exit_time > entry_time:
                                new_entries.append({
                                    "employee_id": emp_id,
                                    "timestamp": entry_time.isoformat(timespec='seconds'),
                                    "type": "entrada"
                                })
                                new_entries.append({
                                    "employee_id": emp_id,
                                    "timestamp": exit_time.isoformat(timespec='seconds'),
                                    "type": "salida"
                                })
                        except ValueError: 
                            print(f"Error generando fecha para {emp_id} en {current_date}")

            current_date += datetime.timedelta(days=1) # Siguiente día

        history.extend(new_entries)
        
        try:
            with open(asistencia_historico_path, "w", encoding='utf-8') as f:
                json.dump(history, f, indent=4, ensure_ascii=False)
            print(f"✅ {len(new_entries)} registros aleatorios añadidos a {asistencia_historico_path}")
            QMessageBox.information(self, "Éxito", f"Se generaron y añadieron {len(new_entries)//2} días de trabajo aleatorios al historial.")
            
            # Opcional: Recalcular la nómina automáticamente después de generar
            self.calculate_payroll() 
            
        except IOError as e:
            print(f"❌ Error al guardar el historial de asistencia: {e}")
            QMessageBox.critical(self, "Error", "No se pudo guardar el archivo de historial de asistencia.")


    def update_export_button_state(self):
        """Habilita el botón de exportar PDF solo si hay una fila seleccionada."""
        has_selection = bool(self.payroll_table.selectionModel().selectedRows())
        self.btn_export_pdf.setEnabled(has_selection)

class TableCardWidget(QFrame):

    def __init__(self, table_number, parent=None):
        super().__init__(parent)
        self.setObjectName("table_card")
        self.payroll_daily_details = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(100, 100)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number_label = QLabel(str(table_number))
        number_label.setObjectName("table_card_number")
        number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(number_label)

class ToggleSwitch(QCheckBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(60, 28) 
        self.setObjectName("toggle_switch")

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)
    
class PlatilloItemWidget(QWidget):

    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.item_id = item_data.get("id")
        self.disponible = item_data.get("disponible", True) 
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(15)
        self.image_label = QLabel()
        self.image_label.setFixedSize(50, 50) 
        self.image_label.setObjectName("menu_item_image")
        
        imagen_path = os.path.join(BASE_DIR, "assets", item_data.get("imagen", "default.png"))
        pixmap = QPixmap(imagen_path)
        self.image_label.setPixmap(pixmap.scaled(50, 50, 
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.image_label)
        self.text_label = QLabel(item_data.get("nombre", "N/A"))
        self.text_label.setObjectName("menu_item_label")
        layout.addWidget(self.text_label)
        layout.addStretch() 
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.actualizarApariencia() 
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def actualizarApariencia(self):
        """Ajusta la opacidad basado en el estado 'disponible'."""
        if self.disponible:
            self.opacity_effect.setOpacity(1.0)
            self.text_label.setStyleSheet("text-decoration: none;")
        else:
            self.opacity_effect.setOpacity(0.4)
            self.text_label.setStyleSheet("text-decoration: line-through;") 

    def mousePressEvent(self, event):
        """Al hacer clic, cambia el estado y actualiza la apariencia."""
        self.disponible = not self.disponible
        self.actualizarApariencia()
        print(f"Item {self.item_id} marcado como: {'Disponible' if self.disponible else 'Agotado'}")
        super().mousePressEvent(event)

class RoleCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon_path, title, role_name, parent=None):
        super().__init__(parent)
        self.setObjectName("role_card")
        self.setFixedSize(180, 180)
        self.role_name = role_name
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        icon_label = QLabel()
        icon_pixmap = QPixmap(icon_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setObjectName("role_card_title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class RoleSelectionPage(QWidget):
    role_selected = pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("role_selection_page")
        
        self.title = QLabel("Selección de Rol", parent=self)
        self.title.setObjectName("main_title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.cards_container = QWidget(parent=self)
        
        cashier_icon_path = os.path.join(BASE_DIR,"Assets", "icon_cashier.png")
        admin_icon_path = os.path.join(BASE_DIR, "Assets", "icon_admin.png")
        cook_icon_path = os.path.join(BASE_DIR,"Assets",  "icon_cook.png")
    
        self.card_cashier = RoleCard(cashier_icon_path, "Cajero", "Cajero", parent=self.cards_container)
        self.card_admin = RoleCard(admin_icon_path, "Administrador", "Administrador", parent=self.cards_container)
        self.card_cook = RoleCard(cook_icon_path, "Cocinero", "Cocinero", parent=self.cards_container)
        
        self.all_cards = [self.card_cashier, self.card_admin, self.card_cook]
        self.initial_geometries = {}
        self._initial_setup_done = False
        self.card_cashier.clicked.connect(lambda: self.start_animation(self.card_cashier))
        self.card_admin.clicked.connect(lambda: self.start_animation(self.card_admin))
        self.card_cook.clicked.connect(lambda: self.start_animation(self.card_cook))
        
        self.current_animation_group = None

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initial_setup_done:
            self.setup_initial_positions()
            self._initial_setup_done = True
        self.reset_state()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._initial_setup_done:
            self.recenter_elements()

    def setup_initial_positions(self):
        card_width = self.card_cashier.width()
        spacing = 30
        positions = [0, card_width + spacing, 2 * (card_width + spacing)]
        for card, pos_x in zip(self.all_cards, positions):
            card.move(pos_x, 0)
            self.initial_geometries[card] = card.geometry()
        total_width = 3 * card_width + 2 * spacing
        self.cards_container.setFixedSize(total_width, self.card_cashier.height())
        QTimer.singleShot(0, self.recenter_elements)
        
    def recenter_elements(self):
        """Recalcula el centro de la página y reposiciona los elementos."""
        if not self.isVisible():
            return
        self.title.adjustSize() 
        title_x = (self.width() - self.title.width()) // 2
        title_y = int(self.height() * 0.25)
        self.title.move(title_x, title_y)
        
        cards_container_x = (self.width() - self.cards_container.width()) // 2
        cards_container_y = int(self.height() * 0.5) - (self.cards_container.height() // 2)
        self.cards_container.move(cards_container_x, cards_container_y)

    def reset_state(self):
        if not self._initial_setup_done:
            return
            
        self.recenter_elements()
        
        self.title.show()
        self.title.raise_() 
        self.cards_container.show()
        
        for card in self.all_cards:
            card.setGeometry(self.initial_geometries[card])
            if card.graphicsEffect():
                card.graphicsEffect().deleteLater()
                card.setGraphicsEffect(None)
            card.setEnabled(True)
            card.show()

    def start_animation(self, selected_card):
        original_selected_card_pos_in_container = selected_card.pos()
        global_pos = selected_card.mapToGlobal(QPoint(0, 0))
        selected_card_page_pos = self.mapFromGlobal(global_pos)
        selected_card.setParent(self)
        selected_card.move(selected_card_page_pos)
        selected_card.raise_()
        selected_card.show() 
        other_cards = [card for card in self.all_cards if card is not selected_card]
        for card in self.all_cards:
            card.setEnabled(False)
        
        anim_group_disappear = QParallelAnimationGroup()
        for card in other_cards:
            opacity_effect = QGraphicsOpacityEffect(card)
            card.setGraphicsEffect(opacity_effect)
            anim_fade = QPropertyAnimation(opacity_effect, b"opacity")
            anim_fade.setDuration(300)
            anim_fade.setEndValue(0.0)
            anim_fade.setEasingCurve(QEasingCurve.Type.InQuad)
            
            anim_slide = QPropertyAnimation(card, b"pos")
            anim_slide.setDuration(300)
            anim_slide.setEndValue(QPoint(card.pos().x(), card.pos().y() - 80))
            anim_slide.setEasingCurve(QEasingCurve.Type.InQuad)
            anim_group_disappear.addAnimation(anim_fade)
            anim_group_disappear.addAnimation(anim_slide)
        
        center_x = (self.width() - selected_card.width()) // 2
        center_y = (self.height() - selected_card.height()) // 2
        
        anim_move_to_center = QPropertyAnimation(selected_card, b"pos")
        anim_move_to_center.setDuration(400)
        anim_move_to_center.setEndValue(QPoint(center_x, center_y))
        anim_move_to_center.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        current_size = selected_card.size() 
        new_width = int(current_size.width() * 1.2)
        new_height = int(current_size.height() * 1.2)
        end_x = center_x - (new_width - current_size.width()) // 2
        end_y = center_y - (new_height - current_size.height()) // 2
        end_rect = QRect(end_x, end_y, new_width, new_height)
        anim_scale_and_center = QPropertyAnimation(selected_card, b"geometry")
        anim_scale_and_center.setDuration(300)
        anim_scale_and_center.setEndValue(end_rect)
        anim_scale_and_center.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim_group_selected = QSequentialAnimationGroup()
        anim_group_selected.addAnimation(anim_move_to_center)
        anim_group_selected.addAnimation(anim_scale_and_center) 
        anim_title_slide = QPropertyAnimation(self.title, b"pos")
        anim_title_slide.setDuration(400)
        anim_title_slide.setEasingCurve(QEasingCurve.Type.InCubic)
        anim_title_slide.setEndValue(QPoint(-self.title.width(), self.title.y()))
        
        final_animation_group = QParallelAnimationGroup()
        final_animation_group.addAnimation(anim_group_disappear)
        final_animation_group.addAnimation(anim_group_selected)
        final_animation_group.addAnimation(anim_title_slide)
        final_animation_group.finished.connect(lambda: self.on_animation_finished(selected_card, original_selected_card_pos_in_container))
        
        self.current_animation_group = final_animation_group
        self.current_animation_group.start()

    def on_animation_finished(self, selected_card, original_pos_in_container):
        selected_card.setParent(self.cards_container)
        selected_card.move(original_pos_in_container)
        selected_card.show()
        self.role_selected.emit(selected_card.role_name)
        
class MainWindow(QMainWindow):

    trigger_server_stop = pyqtSignal()

    def update_and_save_config(self, updated_config):
        self.app_config = updated_config 
        self.save_app_config() 

    def load_app_config(self):
        self.config_file_path = os.path.join(BASE_DIR, "assets", "config.json")
        try:
            with open(self.config_file_path, "r") as f:
                self.app_config = json.load(f)
            print(f"⚙️ Configuración cargada desde {self.config_file_path}")
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ No se encontró config.json o está corrupto. Usando config por defecto.")
            self.app_config = {"total_mesas": 10} 

    def save_app_config(self):
        try:
            with open(self.config_file_path, "w") as f:
                json.dump(self.app_config, f, indent=4)
            print(f"💾 Configuración guardada en {self.config_file_path}")
        except IOError:
            print("❌ Error al guardar la configuración.")
    
    def sync_employee_data(self, updated_data):
        print("🔄 Sincronizando datos de empleados entre Admin y Asistencia...")
        self.page_attendance.update_employee_data(updated_data)

    def actualizar_tabla_asistencia(self, datos):
        print(f"🔄 Señal recibida en MainWindow, pasando datos a la tabla: {datos}")
        self.page_attendance.registrar_asistencia(datos)
    
    def distribuir_orden(self, orden_completa):
        print("🧠 Distribuyendo orden a Cocina y Caja...")
        datos_cocina = {
            "numero_mesa": orden_completa.get("numero_mesa"),
            "items": [
                {
                    "nombre": item.get("nombre"), 
                    "cantidad": item.get("cantidad"), 
                    "notas": item.get("notas"),
                    "imagen": item.get("imagen") 
                }
                for item in orden_completa.get("items", [])
            ]
        }
        self.page_cocina.agregar_orden(datos_cocina)
        
        self.page_caja.agregar_orden(orden_completa)

    def __init__(self):
        super().__init__()
        self.load_app_config()
        self.setWindowTitle("El Puestito - Sistema de Gestión")
        self.setMinimumSize(1200, 800)
        self.current_role = None
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.sidebar = self.create_sidebar()
        self.btn_qr.clicked.connect(self.show_qr_dialog)
        self.stacked_widget = QStackedWidget()
        self.page_attendance = AttendancePage()
        employee_data = self.page_attendance.get_employees_data()
        self.page_role_selection = RoleSelectionPage()
        self.page_cocina = CocinaPage()
        self.page_caja = CajaPage()
        self.page_admin = AdminPage(employee_data, self.app_config)
        self.page_admin.employees_updated.connect(self.sync_employee_data)
        self.page_admin.config_updated.connect(self.update_and_save_config)
        self.stacked_widget.addWidget(self.page_attendance)
        self.stacked_widget.addWidget(self.page_role_selection)
        self.stacked_widget.addWidget(self.page_cocina)
        self.stacked_widget.addWidget(self.page_caja)
        self.stacked_widget.addWidget(self.page_admin)
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stacked_widget)
        self.load_stylesheet("style.qss")
        self.page_role_selection.role_selected.connect(self.handle_role_selection)

        # --- INICIO DE LA LÓGICA DE HILO CORREGIDA ---
        print("Creando ServerWorker en Hilo Principal...")
        self.server_worker = ServerWorker() 

        print("Creando ServerThread...")

        self.thread = ServerThread(worker_instance=self.server_worker)
        self.server_worker.asistencia_recibida.connect(self.actualizar_tabla_asistencia)
        self.server_worker.nueva_orden_recibida.connect(self.distribuir_orden)

        self.thread.start()
        print("🚀 Servidor de asistencia iniciado en segundo plano.")
        
    def show_qr_dialog(self):
        dialog = QRCodeDialog(self)
        dialog.exec()
    
    def actualizar_tabla_asistencia(self, datos):
        print(f"🔄 Señal recibida en MainWindow, pasando datos a la tabla: {datos}")
        self.page_attendance.registrar_asistencia(datos)

    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        logo_label = QLabel()
        logo_path = os.path.join(BASE_DIR,"Assets","logo.png")
        logo_pixmap = QPixmap(logo_path).scaledToWidth(150, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
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
        if role_name == "Cocinero":
            self.stacked_widget.setCurrentWidget(self.page_cocina)
        elif role_name == "Cajero":
            self.stacked_widget.setCurrentWidget(self.page_caja)
        elif role_name == "Administrador":
            self.stacked_widget.setCurrentWidget(self.page_admin)
    
    def load_stylesheet(self, filename):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            absolute_path = os.path.join(script_dir, "assets", filename) 
            print(f"Intentando cargar la hoja de estilos desde: {absolute_path}")

            with open(absolute_path, "r", encoding = "utf-8") as f:
                self.setStyleSheet(f.read())
                
        except FileNotFoundError:
            print(f"ADVERTENCIA: No se encontró el archivo de estilos '{filename}' en la ruta calculada.")

    def closeEvent(self, event):
        print("Cerrando la aplicación, guardando datos...")

        if hasattr(self, 'thread') and self.thread.isRunning():
            print("[MainThread] Deteniendo el hilo del servidor...")
            print("[MainThread] Llamando a self.server_worker.stop_server()...")

            self.server_worker.stop_server() 
            
            print("[MainThread] Esperando finalización del hilo (wait)...")
            if not self.thread.wait(3000): 
                print("[MainThread] ADVERTENCIA: El hilo del servidor tardó demasiado en cerrarse, forzando terminación.")
                self.thread.terminate() 
            else:
                print("✅ [MainThread] Hilo del servidor detenido limpiamente.")
        
        if hasattr(self, 'page_attendance'):
            self.page_attendance.save_data_to_file() 
        if hasattr(self, 'server_worker'):
            self.server_worker.save_ids_to_file() 
        if hasattr(self, 'page_cocina'):
            self.page_cocina.save_active_orders() 
        if hasattr(self, 'page_caja'):
            self.page_caja.save_active_orders() 
            
        self.save_app_config()   
        super().closeEvent(event) 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())