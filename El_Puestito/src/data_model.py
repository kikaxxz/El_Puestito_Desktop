# Contenido para: src/data_model.py

import sqlite3
import os
import threading
import json
import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "assets", "puestito.db") # La nueva BD vivirá junto a tus JSON
JSON_ASSETS_DIR = os.path.join(BASE_DIR, "assets")

class DataManager:
    """
    Esta clase es ahora la ÚNICA responsable de hablar con la base de datos.
    Maneja las conexiones de forma segura para múltiples hilos (GUI y Servidor).
    """

    def __init__(self, db_path):
        self.db_path = db_path
        self.local = threading.local()
        print(f"🗃️  DataManager inicializado. Conectando a: {self.db_path}")

    def get_conn(self):
        """Obtiene o crea una conexión a la BD para el hilo actual."""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path)
            self.local.conn.row_factory = sqlite3.Row 
        return self.local.conn

    def close_conn_for_thread(self):
        """Cierra la conexión para el hilo actual (ej. al cerrar un hilo)."""
        if hasattr(self.local, 'conn'):
            self.local.conn.close()
            del self.local.conn

    def execute(self, query, params=()):
        """Ejecuta una consulta de escritura (INSERT, UPDATE, DELETE)."""
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"❌ Error en DataManager.execute: {e}\nQuery: {query}")
            return None

    def fetchone(self, query, params=()):
        """Busca un solo registro."""
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            # Convertimos la fila a un diccionario simple para desacoplarlo
            return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"❌ Error en DataManager.fetchone: {e}\nQuery: {query}")
            return None

    def fetchall(self, query, params=()):
        """Busca todos los registros que coinciden."""
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            # Convertimos las filas a una lista de diccionarios
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"❌ Error en DataManager.fetchall: {e}\nQuery: {query}")
            return []


    def create_tables(self):
        """
        Crea toda la estructura de la base de datos si no existe.
        Esto reemplaza la necesidad de que los archivos JSON existan.
        """
        print("Creando tablas si no existen...")
        self.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id_empleado TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            rol TEXT,
            deviceId TEXT UNIQUE
        );
        """)

        # --- INICIO DE LA CORRECCIÓN ---

        # MOVIDA AQUÍ: Crear 'menu_categorias' PRIMERO
        self.execute("""
        CREATE TABLE IF NOT EXISTS menu_categorias (
            id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        );
        """)
        
        # Ahora 'menu_items' puede referenciarla sin error
        self.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id_item TEXT PRIMARY KEY,
            id_categoria INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio REAL NOT NULL,
            imagen TEXT,
            disponible INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (id_categoria) REFERENCES menu_categorias (id_categoria)
        );
        """)

        self.execute("""
        CREATE TABLE IF NOT EXISTS eventos_asistencia (
            id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_empleado TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            tipo TEXT NOT NULL,
            FOREIGN KEY (id_empleado) REFERENCES empleados (id_empleado)
        );
        """)

        self.execute("""
        CREATE TABLE IF NOT EXISTS ordenes (
            id_orden INTEGER PRIMARY KEY AUTOINCREMENT,
            mesa_key TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'activa',
            fecha_apertura DATETIME NOT NULL,
            fecha_cierre DATETIME,
            client_uuid TEXT UNIQUE
        );
        """)

        self.execute("""
        CREATE TABLE IF NOT EXISTS orden_detalle (
            id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
            id_orden INTEGER NOT NULL,
            id_item_menu TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario_congelado REAL NOT NULL,
            nombre_congelado TEXT NOT NULL,
            imagen_congelada TEXT,
            notas TEXT,
            destino TEXT NOT NULL,
            estado_item TEXT NOT NULL DEFAULT 'pendiente',
            FOREIGN KEY (id_orden) REFERENCES ordenes (id_orden),
            FOREIGN KEY (id_item_menu) REFERENCES menu_items (id_item)
        );
        """)
        print("✅ Tablas listas.")


    def run_migration_if_needed(self):
        """
        Revisa si la base de datos está vacía y, de ser así,
        importa los datos desde los antiguos archivos JSON.
        """
        if not self.fetchone("SELECT id_empleado FROM empleados LIMIT 1"):
            print("Base de datos vacía detectada. Iniciando migración de datos desde JSON...")
            self._migrate_employees()
            self._migrate_attendance_history()
            self._migrate_menu()
            print("✅ Migración de datos completada.")
        else:
            print("Base de datos ya poblada. No se requiere migración.")

    def _migrate_employees(self):
        """Importa datos desde asistencia.json a la tabla empleados."""
        json_path = os.path.join(JSON_ASSETS_DIR, "asistencia.json")
        try:
            with open(json_path, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            for emp in data:
                self.execute(
                    "INSERT OR IGNORE INTO empleados (id_empleado, nombre, rol, deviceId) VALUES (?, ?, ?, ?)",
                    (emp.get('id'), emp.get('nombre'), emp.get('rol'), emp.get('deviceId'))
                )
            print(f"Migrados {len(data)} empleados desde {json_path}")
        except FileNotFoundError:
            print(f"⚠️ No se encontró {json_path} para migrar empleados.")
        except Exception as e:
            print(f"❌ Error migrando empleados: {e}")

    def _migrate_attendance_history(self):
        """Importa datos desde asistencia_historico.json."""
        json_path = os.path.join(JSON_ASSETS_DIR, "asistencia_historico.json")
        try:
            with open(json_path, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            for ev in data:
                self.execute(
                    "INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES (?, ?, ?)",
                    (ev.get('employee_id'), ev.get('timestamp'), ev.get('type'))
                )
            print(f"Migrados {len(data)} eventos de asistencia desde {json_path}")
        except FileNotFoundError:
            print(f"⚠️ No se encontró {json_path} para migrar historial.")
        except Exception as e:
            print(f"❌ Error migrando historial de asistencia: {e}")

    def _migrate_menu(self):
        """Importa datos desde menu.json a las tablas de menú."""
        json_path = os.path.join(JSON_ASSETS_DIR, "menu.json")
        try:
            with open(json_path, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            item_count = 0
            for cat in data.get('categorias', []):
                cat_nombre = cat.get('nombre')
                # Inserta la categoría y obtiene su ID
                self.execute("INSERT OR IGNORE INTO menu_categorias (nombre) VALUES (?)", (cat_nombre,))
                cat_db = self.fetchone("SELECT id_categoria FROM menu_categorias WHERE nombre = ?", (cat_nombre,))
                cat_id = cat_db['id_categoria']
                
                for item in cat.get('items', []):
                    self.execute(
                        """
                        INSERT OR IGNORE INTO menu_items 
                        (id_item, id_categoria, nombre, descripcion, precio, imagen, disponible)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.get('id'), cat_id, item.get('nombre'),
                            item.get('descripcion'),
                            item.get('precio'), item.get('imagen'),
                            int(item.get('disponible', True))
                        )
                    )
                    item_count += 1

            print(f"Migrados {item_count} items de menú desde {json_path}")
        except FileNotFoundError:
            print(f"⚠️ No se encontró {json_path} para migrar menú.")
        except Exception as e:
            print(f"❌ Error migrando menú: {e}")

    
    def get_employees(self):
        """REEMPLAZA: _load_employee_data() y get_employees_data()."""
        return self.fetchall("SELECT * FROM empleados ORDER BY nombre;")

    def get_employee_by_id(self, employee_id):
        """Obtiene un solo empleado por su ID."""
        return self.fetchone("SELECT * FROM empleados WHERE id_empleado = ?;", (employee_id,))

    def get_employee_by_device(self, device_id):
        """Obtiene un solo empleado por su deviceId."""
        return self.fetchone("SELECT * FROM empleados WHERE deviceId = ?;", (device_id,))
        
    def add_employee(self, id, nombre, rol):
        """REEMPLAZA: La lógica de 'add_employee' en AdminPage."""
        return self.execute(
            "INSERT INTO empleados (id_empleado, nombre, rol) VALUES (?, ?, ?);",
            (id, nombre, rol)
        )

    def update_employee(self, id_original, new_id, new_name, new_rol):
        """REEMPLAZA: La lógica de 'edit_employee' en AdminPage."""
        return self.execute(
            "UPDATE empleados SET id_empleado = ?, nombre = ?, rol = ? WHERE id_empleado = ?;",
            (new_id, new_name, new_rol, id_original)
        )
        
    def delete_employee(self, employee_id):
        """REEMPLAZA: La lógica de 'delete_employee' en AdminPage."""

        try:
            return self.execute("DELETE FROM empleados WHERE id_empleado = ?;", (employee_id,))
        except sqlite3.IntegrityError:
            print(f"No se puede borrar empleado {employee_id}, tiene historial. Desactivar en su lugar (lógica pendiente).")
            return None

    def link_device_to_employee(self, employee_id, device_id):
        """REEMPLAZA: Parte de la lógica de 'registrar_asistencia_movil'."""
        return self.execute(
            "UPDATE empleados SET deviceId = ? WHERE id_empleado = ?;",
            (device_id, employee_id)
        )

    def add_attendance_event(self, employee_id, event_type, timestamp):
        """REEMPLAZA: _log_attendance_event()."""
        return self.execute(
            "INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES (?, ?, ?);",
            (employee_id, timestamp, event_type)
        )
        
    def get_attendance_history_range(self, start_date, end_date):
        """REEMPLAZA: La lectura de asistencia_historico.json en 'calculate_payroll'."""
        return self.fetchall(
            """
            SELECT e.nombre, e.rol, ev.timestamp, ev.tipo, ev.id_empleado
            FROM eventos_asistencia ev
            JOIN empleados e ON ev.id_empleado = e.id_empleado
            WHERE ev.timestamp BETWEEN ? AND ?
            ORDER BY ev.id_empleado, ev.timestamp;
            """,
            (start_date, end_date)
        )
        
    def clear_all_attendance_history(self):
        """REEMPLAZA: La parte de 'limpiar_registros' que borra el historial."""
        print("Borrando todo el historial de eventos de asistencia...")
        return self.execute("DELETE FROM eventos_asistencia;")

    # --- Métodos de Menú ---

    def get_menu_with_categories(self):
        """REEMPLAZA: La lectura de menu.json en 'load_menu_data' y 'get_menu'."""
        categorias = self.fetchall("SELECT * FROM menu_categorias ORDER BY nombre;")
        items = self.fetchall("SELECT * FROM menu_items;")
        
        menu_completo = {"categorias": []}
        items_por_categoria = {}
        for item in items:
            cat_id = item['id_categoria']
            if cat_id not in items_por_categoria:
                items_por_categoria[cat_id] = []
            items_por_categoria[cat_id].append(item)
            
        for cat in categorias:
            menu_completo["categorias"].append({
                "nombre": cat['nombre'],
                "items": items_por_categoria.get(cat['id_categoria'], [])
            })
        return menu_completo

    def get_available_menu_items(self):
        """Obtiene un set de IDs de items disponibles. REEMPLAZA: _validate_order_items."""
        rows = self.fetchall("SELECT id_item FROM menu_items WHERE disponible = 1;")
        return {row['id_item'] for row in rows}

    def update_menu_item_availability(self, item_id, is_available):
        """REEMPLAZA: La lógica de 'save_menu_data' (se llamaría en un bucle)."""
        return self.execute(
            "UPDATE menu_items SET disponible = ? WHERE id_item = ?;",
            (int(is_available), item_id)
        )
    def get_last_attendance_event(self, employee_id):
        """
        Encuentra el último evento (entrada o salida) de un empleado específico
        para determinar cuál debe ser el siguiente.
        """
        return self.fetchone(
            "SELECT tipo FROM eventos_asistencia WHERE id_empleado = ? ORDER BY timestamp DESC LIMIT 1;",
            (employee_id,)
        )

    def get_first_unlinked_employee(self):
        """
        Busca al primer empleado en la base de datos que no tenga un
        deviceId asignado (que sea NULL o una cadena vacía).
        """
        return self.fetchone(
            "SELECT * FROM empleados WHERE deviceId IS NULL OR deviceId = '' ORDER BY nombre LIMIT 1;"
        )

    def get_sales_report(self, date_str):
        """
        REEMPLAZA: La lectura de ventas_completadas.json en 'mostrar_reporte_del_dia'.
        Obtiene el total de ventas y los items más vendidos para una fecha específica.
        
        'date_str' debe estar en formato 'YYYY-MM-DD'.
        """
        
        total_query = """
        SELECT SUM(d.cantidad * d.precio_unitario_congelado) AS total
        FROM ordenes o
        JOIN orden_detalle d ON o.id_orden = d.id_orden
        WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) = DATE(?);
        """
        total_result = self.fetchone(total_query, (date_str,))
        total_ventas = total_result['total'] if total_result and total_result['total'] else 0.0

        # 2. Obtener los items más vendidos
        items_query = """
        SELECT 
            d.id_item_menu,
            m.nombre,
            SUM(d.cantidad) AS cantidad_total
        FROM ordenes o
        JOIN orden_detalle d ON o.id_orden = d.id_orden
        JOIN menu_items m ON d.id_item_menu = m.id_item
        WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) = DATE(?)
        GROUP BY d.id_item_menu, m.nombre
        ORDER BY cantidad_total DESC;
        """
        items_vendidos = self.fetchall(items_query, (date_str,))
        
        return total_ventas, items_vendidos

    def add_attendance_events_batch(self, events_list):
        """
        REEMPLAZA: La escritura a asistencia_historico.json en 'generate_random_attendance'.
        Inserta una lista de eventos de asistencia en lote (mucho más rápido).
        
        'events_list' debe ser una lista de tuplas: (id_empleado, timestamp_iso, tipo)
        """
        query = "INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES (?, ?, ?);"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.executemany(query, events_list)
            conn.commit()
            print(f"Insertados {len(events_list)} eventos en lote.")
            return True
        except sqlite3.Error as e:
            print(f"❌ Error en DataManager.add_attendance_events_batch: {e}")
            return False
    

    def get_events_for_today(self):
        """
        Obtiene todos los eventos de asistencia (entrada/salida) que
        hayan ocurrido en la fecha actual.
        """
        today_str = datetime.date.today().isoformat()
        query = """
        SELECT id_empleado, tipo, MAX(timestamp) as last_timestamp
        FROM eventos_asistencia
        WHERE DATE(timestamp) = DATE(?)
        GROUP BY id_empleado, tipo
        ORDER BY last_timestamp;
        """
        return self.fetchall(query, (today_str,))
    
    # --- MÉTODOS DE ÓRDENES (REEMPLAZAN JSON) ---

    def check_duplicate_order_id(self, client_uuid):
        """
        Verifica si un client_uuid ya existe en la tabla de órdenes.
        REEMPLAZA: La lógica de processed_orders.json
        """
        query = "SELECT id_orden FROM ordenes WHERE client_uuid = ?;"
        result = self.fetchone(query, (client_uuid,))
        return result is not None

    def create_new_order(self, orden_completa):
        """
        Crea una nueva orden activa, incluyendo sus detalles, en una transacción.
        REEMPLAZA: agregar_orden en CajaPage, CocinaPage, BarraPage
        """
        PREFIJOS_BEBIDAS = ("MIC", "OBA", "BSA", "CER", "RTD")
        
        conn = self.get_conn()
        cursor = conn.cursor()
        
        try:
            # 1. Crear la llave de la mesa
            mesa_principal = str(orden_completa['numero_mesa'])
            mesas_enlazadas = orden_completa.get('mesas_enlazadas', [])
            
            mesa_key = ""
            if mesas_enlazadas and len(mesas_enlazadas) > 0:
                todas_las_mesas_list = [mesa_principal] + [str(m) for m in mesas_enlazadas]
                mesas_str_list = sorted(todas_las_mesas_list)
                mesa_key = "+".join(mesas_str_list)
            else:
                mesa_key = mesa_principal

            # 2. Insertar la orden principal
            timestamp = orden_completa.get('timestamp', datetime.datetime.now().isoformat())
            client_uuid = orden_completa.get('order_id')
            
            cursor.execute(
                """
                INSERT INTO ordenes (mesa_key, estado, fecha_apertura, client_uuid)
                VALUES (?, 'activa', ?, ?);
                """,
                (mesa_key, timestamp, client_uuid)
            )
            id_orden = cursor.lastrowid
            
            # 3. Preparar los detalles de la orden
            detalle_batch = []
            for item in orden_completa.get('items', []):
                item_id = item.get('item_id')
                destino = 'barra' if any(item_id.startswith(p) for p in PREFIJOS_BEBIDAS) else 'cocina'
                
                detalle_batch.append((
                    id_orden,
                    item_id,
                    item.get('cantidad'),
                    item.get('precio_unitario'),
                    item.get('nombre'),
                    item.get('imagen'),
                    item.get('notas', ''),
                    destino
                ))
            
            # 4. Insertar todos los detalles en lote
            cursor.executemany(
                """
                INSERT INTO orden_detalle (
                    id_orden, id_item_menu, cantidad, precio_unitario_congelado,
                    nombre_congelado, imagen_congelada, notas, destino
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                detalle_batch
            )
            
            # 5. Confirmar la transacción
            conn.commit()
            print(f"✅ Orden {id_orden} (Mesa {mesa_key}) creada exitosamente.")
            return id_orden
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"❌ Error en create_new_order (haciendo rollback): {e}")
            return None

    def get_active_orders_caja(self):
        """
        Obtiene todas las órdenes activas y sus detalles, formateadas como el
        antiguo caja_ordenes.json.
        REEMPLAZA: load_active_orders en CajaPage y /estado-mesas
        """
        query = """
        SELECT
            o.id_orden, o.mesa_key, o.fecha_apertura,
            d.cantidad, d.precio_unitario_congelado AS precio_unitario,
            d.nombre_congelado AS nombre, d.imagen_congelada AS imagen,
            d.notas, d.id_item_menu AS item_id
        FROM ordenes o
        JOIN orden_detalle d ON o.id_orden = d.id_orden
        WHERE o.estado = 'activa'
        ORDER BY o.fecha_apertura;
        """
        rows = self.fetchall(query)
        
        caja_data = {}
        for row in rows:
            mesa_key = row['mesa_key']
            if mesa_key not in caja_data:
                caja_data[mesa_key] = {
                    'id_orden_db': row['id_orden'],
                    'fecha_apertura': row['fecha_apertura'],
                    'items': []
                }
            
            # Crea el diccionario de item
            item_dict = {
                'item_id': row['item_id'],
                'nombre': row['nombre'],
                'cantidad': row['cantidad'],
                'precio_unitario': row['precio_unitario'],
                'imagen': row['imagen'],
                'notas': row['notas']
            }
            caja_data[mesa_key]['items'].append(item_dict)
            
        return caja_data

    def _get_active_orders_by_destino(self, destino_busqueda):
        """
        Función base interna para Cocina y Barra.
        Obtiene todos los items PENDIENTES para un destino.
        """
        query = """
        SELECT
            o.mesa_key,
            d.nombre_congelado AS nombre,
            d.cantidad,
            d.notas,
            d.imagen_congelada AS imagen
        FROM ordenes o
        JOIN orden_detalle d ON o.id_orden = d.id_orden
        WHERE o.estado = 'activa'
        AND d.destino = ?
        AND d.estado_item = 'pendiente'
        ORDER BY o.fecha_apertura;
        """
        rows = self.fetchall(query, (destino_busqueda,))
        
        # Agrupar por mesa_key para que coincida con el formato de ticket
        ordenes_dict = {}
        for item in rows:
            mesa_key = item['mesa_key']
            if mesa_key not in ordenes_dict:
                ordenes_dict[mesa_key] = {
                    'numero_mesa': mesa_key, # 'numero_mesa' es lo que espera el OrderTicketWidget
                    'items': []
                }
            
            item_ticket = {
                'nombre': item['nombre'],
                'cantidad': item['cantidad'],
                'notas': item['notas'],
                'imagen': item['imagen']
            }
            ordenes_dict[mesa_key]['items'].append(item_ticket)
        
        return list(ordenes_dict.values()) # Convertir de dict a lista

    def get_active_cocina_orders(self):
        """
        Obtiene todas las órdenes de cocina PENDIENTES.
        REEMPLAZA: load_active_orders en CocinaPage
        """
        return self._get_active_orders_by_destino('cocina')
        
    def get_active_barra_orders(self):
        """
        Obtiene todas las órdenes de barra PENDIENTES.
        REEMPLAZA: load_active_orders en BarraPage
        """
        return self._get_active_orders_by_destino('barra')

    def _mark_order_items_ready(self, mesa_key, destino_busqueda):
        """
        Función base interna para Cocina y Barra.
        Marca todos los items PENDIENTES de una mesa como 'listo'.
        """
        query = """
        UPDATE orden_detalle
        SET estado_item = 'listo'
        WHERE destino = ?
        AND estado_item = 'pendiente'
        AND id_orden IN (
            SELECT id_orden FROM ordenes WHERE mesa_key = ? AND estado = 'activa'
        );
        """
        return self.execute(query, (destino_busqueda, mesa_key))

    def mark_cocina_order_ready(self, mesa_key):
        """
        Marca todos los items de cocina pendientes para una mesa como 'listo'.
        REEMPLAZA: remover_orden en CocinaPage
        """
        print(f"DB: Marcando items de COCINA listos para mesa {mesa_key}")
        return self._mark_order_items_ready(mesa_key, 'cocina')
        
    def mark_barra_order_ready(self, mesa_key):
        """
        Marca todos los items de barra pendientes para una mesa como 'listo'.
        REEMPLAZA: remover_orden en BarraPage
        """
        print(f"DB: Marcando items de BARRA listos para mesa {mesa_key}")
        return self._mark_order_items_ready(mesa_key, 'barra')

    def complete_order(self, mesa_key):
        """
        Cierra una orden activa, marcándola como 'cerrada' y
        estableciendo la fecha de cierre.
        REEMPLAZA: lógica de 'cobrar_cuenta' (pop, save_active, guardar_venta)
        """
        print(f"DB: Cerrando orden para mesa {mesa_key}")
        
        orden_a_cerrar = self.get_active_orders_caja().get(mesa_key)
        
        if not orden_a_cerrar:
            print(f"DB: No se encontró orden activa para {mesa_key} al intentar cerrar.")
            return None
        
        timestamp = datetime.datetime.now().isoformat()
        query = """
        UPDATE ordenes
        SET estado = 'cerrada', fecha_cierre = ?
        WHERE mesa_key = ? AND estado = 'activa';
        """
        self.execute(query, (timestamp, mesa_key))
        
        return orden_a_cerrar