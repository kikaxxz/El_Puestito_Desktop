import sqlite3
import os
import threading
import json
import datetime
import uuid
from logger_setup import setup_logger
from path_manager import get_persistent_path, get_asset_path

logger = setup_logger()

DB_PATH = get_persistent_path("puestito.db")

JSON_ASSETS_DIR = get_asset_path("")

class DataManager:

    def __init__(self, db_path):
        self.db_path = db_path
        self.local = threading.local()
        logger.info(f"DataManager inicializado. Conectando a: {self.db_path}")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")

        self.create_tables()
        self._check_and_update_schema()
        self.run_migration_if_needed()

    def get_inventario_completo(self):
        query = """
        SELECT i.id_inventario, i.nombre, i.cantidad, i.es_automatico, i.id_menu_vinculado, m.nombre as nombre_menu
        FROM inventario i
        LEFT JOIN menu_items m ON i.id_menu_vinculado = m.id_item
        ORDER BY i.nombre;
        """
        return self.fetchall(query)

    def agregar_item_inventario(self, nombre, cantidad, es_automatico=0, id_menu_vinculado=None):
        return self.execute(
            "INSERT INTO inventario (nombre, cantidad, es_automatico, id_menu_vinculado) VALUES (?, ?, ?, ?);",
            (nombre, cantidad, es_automatico, id_menu_vinculado)
        )

    def actualizar_cantidad_inventario(self, id_inventario, nueva_cantidad):
        return self.execute(
            "UPDATE inventario SET cantidad = ? WHERE id_inventario = ?;",
            (nueva_cantidad, id_inventario)
        )

    def eliminar_item_inventario(self, id_inventario):
        return self.execute("DELETE FROM inventario WHERE id_inventario = ?;", (id_inventario,))

    def get_conn(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
            self.local.conn.execute("PRAGMA busy_timeout = 30000;") 
        return self.local.conn

    def close_conn_for_thread(self):
        if hasattr(self.local, 'conn'):
            self.local.conn.close()
            del self.local.conn

    def execute(self, query, params=()):
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error en DataManager.execute: {e}\nQuery: {query}")
            return None

    def fetchone(self, query, params=()):
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error en DataManager.fetchone: {e}\nQuery: {query}")
            return None

    def fetchall(self, query, params=()):
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error en DataManager.fetchall: {e}\nQuery: {query}")
            return []

    def create_tables(self):
        logger.info("Verificando tablas de la base de datos...")
        self.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id_empleado TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            rol TEXT,
            deviceId TEXT UNIQUE,
            fingerprint_id INTEGER UNIQUE
        );
        """)

        self.execute("""
        CREATE TABLE IF NOT EXISTS menu_categorias (
            id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            destino TEXT DEFAULT 'cocina' 
        );
        """)
        
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
            client_uuid TEXT UNIQUE,
            proformas_impresas INTEGER NOT NULL DEFAULT 0
        );
        """)

        self.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id_inventario INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            cantidad INTEGER NOT NULL DEFAULT 0,
            es_automatico INTEGER NOT NULL DEFAULT 0,
            id_menu_vinculado TEXT UNIQUE,
            FOREIGN KEY (id_menu_vinculado) REFERENCES menu_items (id_item)
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

    def _check_and_update_schema(self):
        try:
            conn = self.get_conn()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(orden_detalle)")
            columns_det = [info[1] for info in cursor.fetchall()]
            
            if 'id_cerveza' not in columns_det:
                self.execute("ALTER TABLE orden_detalle ADD COLUMN id_cerveza TEXT;")
                self.execute("ALTER TABLE orden_detalle ADD COLUMN nombre_cerveza TEXT;")
            
            cursor.execute("PRAGMA table_info(menu_categorias)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'destino' not in columns:
                logger.info("Esquema desactualizado detectado: Falta columna 'destino' en menu_categorias.")
                logger.info("Aplicando migracion de esquema...")
                
                self.execute("ALTER TABLE menu_categorias ADD COLUMN destino TEXT DEFAULT 'cocina';")
                self._migrate_hardcoded_destinations_to_db()
                logger.info("Esquema actualizado y destinos migrados exitosamente.")

            cursor.execute("PRAGMA table_info(empleados)")
            columns_emp = [info[1] for info in cursor.fetchall()]
            
            if 'fingerprint_id' not in columns_emp:
                logger.info("Esquema: Falta columna 'fingerprint_id' en empleados. Agregando...")
                self.execute("ALTER TABLE empleados ADD COLUMN fingerprint_id INTEGER;")
                self.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_empleados_fingerprint ON empleados(fingerprint_id);")
                logger.info("Columna 'fingerprint_id' agregada correctamente.")
                
            cursor.execute("PRAGMA table_info(ordenes)")
            columns_ordenes = [info[1] for info in cursor.fetchall()]
            
            if 'proformas_impresas' not in columns_ordenes:
                logger.info("Esquema: Falta columna 'proformas_impresas' en ordenes. Agregando...")
                self.execute("ALTER TABLE ordenes ADD COLUMN proformas_impresas INTEGER NOT NULL DEFAULT 0;")
                logger.info("Columna 'proformas_impresas' agregada correctamente.")

        except Exception as e:
            logger.error(f"Error verificando o actualizando esquema: {e}")

    def link_fingerprint_to_employee(self, employee_id, fingerprint_id):
        try:
            self.execute("UPDATE empleados SET fingerprint_id = NULL WHERE fingerprint_id = ?", (fingerprint_id,))
            return self.execute("UPDATE empleados SET fingerprint_id = ? WHERE id_empleado = ?", (fingerprint_id, employee_id))
        except Exception as e:
            logger.error(f"Error vinculando huella: {e}")
            return False
            
    def get_employee_by_fingerprint(self, fingerprint_id):
        return self.fetchone("SELECT * FROM empleados WHERE fingerprint_id = ?", (fingerprint_id,))

    def _migrate_hardcoded_destinations_to_db(self):
        PREFIJOS_ANTIGUOS = ("MIC", "OBA", "BSA", "CER", "RTD")
        
        logger.info("Migrando logica de prefijos a base de datos...")
        categorias = self.fetchall("SELECT id_categoria, nombre FROM menu_categorias")
        
        for cat in categorias:
            cat_id = cat['id_categoria']
            query_items = "SELECT id_item FROM menu_items WHERE id_categoria = ?"
            items = self.fetchall(query_items, (cat_id,))
            
            es_barra = False
            for item in items:
                item_id = item['id_item']
                if any(item_id.startswith(p) for p in PREFIJOS_ANTIGUOS):
                    es_barra = True
                    break
            
            if es_barra:
                logger.info(f"Categoria '{cat['nombre']}' detectada como BARRA. Actualizando BD.")
                self.execute("UPDATE menu_categorias SET destino = 'barra' WHERE id_categoria = ?", (cat_id,))

    def run_migration_if_needed(self):
        if not self.fetchone("SELECT id_empleado FROM empleados LIMIT 1"):
            logger.info("Base de datos vacia detectada. Iniciando migracion de datos desde JSON...")
            self._migrate_employees()
            self._migrate_attendance_history()
            self._migrate_menu()
            logger.info("Migracion de datos completada.")
        else:
            logger.info("Base de datos ya poblada. No se requiere migracion.")

    def _migrate_employees(self):
        json_path = os.path.join(JSON_ASSETS_DIR, "asistencia.json")
        try:
            with open(json_path, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            for emp in data:
                self.execute(
                    "INSERT OR IGNORE INTO empleados (id_empleado, nombre, rol, deviceId) VALUES (?, ?, ?, ?)",
                    (emp.get('id'), emp.get('nombre'), emp.get('rol'), emp.get('deviceId'))
                )
            logger.info(f"Migrados {len(data)} empleados desde {json_path}")
        except FileNotFoundError:
            logger.warning(f"No se encontro {json_path} para migrar empleados.")
        except Exception as e:
            logger.error(f"Error migrando empleados: {e}")

    def _migrate_attendance_history(self):
        json_path = os.path.join(JSON_ASSETS_DIR, "asistencia_historico.json")
        try:
            with open(json_path, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            for ev in data:
                self.execute(
                    "INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES (?, ?, ?)",
                    (ev.get('employee_id'), ev.get('timestamp'), ev.get('type'))
                )
            logger.info(f"Migrados {len(data)} eventos de asistencia desde {json_path}")
        except FileNotFoundError:
            logger.warning(f"No se encontro {json_path} para migrar historial.")
        except Exception as e:
            logger.error(f"Error migrando historial de asistencia: {e}")

    def _migrate_menu(self):
        json_path = os.path.join(JSON_ASSETS_DIR, "menu.json")
        try:
            with open(json_path, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            item_count = 0
            for cat in data.get('categorias', []):
                cat_nombre = cat.get('nombre')
                
                self.execute("INSERT OR IGNORE INTO menu_categorias (nombre, destino) VALUES (?, 'cocina')", (cat_nombre,))
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
            
            self._migrate_hardcoded_destinations_to_db()
            logger.info(f"Migrados {item_count} items de menu desde {json_path}")
        except FileNotFoundError:
            logger.warning(f"No se encontro {json_path} para migrar menu.")
        except Exception as e:
            logger.error(f"Error migrando menu: {e}")

    def get_employees(self):
        return self.fetchall("SELECT * FROM empleados ORDER BY nombre;")

    def get_employee_by_id(self, employee_id):
        return self.fetchone("SELECT * FROM empleados WHERE id_empleado = ?;", (employee_id,))

    def get_employee_by_device(self, device_id):
        return self.fetchone("SELECT * FROM empleados WHERE deviceId = ?;", (device_id,))
        
    def add_employee(self, id, nombre, rol, fingerprint_id=None):
        return self.execute(
            "INSERT INTO empleados (id_empleado, nombre, rol, fingerprint_id) VALUES (?, ?, ?, ?);", 
            (id, nombre, rol, fingerprint_id)
        )

    def update_employee(self, id_original, new_id, new_name, new_rol, fingerprint_id=None):
        return self.execute(
            "UPDATE empleados SET id_empleado = ?, nombre = ?, rol = ?, fingerprint_id = ? WHERE id_empleado = ?;", 
            (new_id, new_name, new_rol, fingerprint_id, id_original)
        )
        
    def delete_employee(self, employee_id):
        try:
            return self.execute("DELETE FROM empleados WHERE id_empleado = ?;", (employee_id,))
        except sqlite3.IntegrityError:
            logger.warning(f"No se puede borrar empleado {employee_id}, tiene historial.")
            return None

    def link_device_to_employee(self, employee_id, device_id):
        return self.execute("UPDATE empleados SET deviceId = ? WHERE id_empleado = ?;", (device_id, employee_id))

    def add_attendance_event(self, employee_id, event_type, timestamp):
        return self.execute("INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES (?, ?, ?);", (employee_id, timestamp, event_type))
        
    def get_attendance_history_range(self, start_date, end_date):
        return self.fetchall("""
            SELECT e.nombre, e.rol, ev.timestamp, ev.tipo, ev.id_empleado
            FROM eventos_asistencia ev
            JOIN empleados e ON ev.id_empleado = e.id_empleado
            WHERE ev.timestamp BETWEEN ? AND ?
            ORDER BY ev.id_empleado, ev.timestamp;
            """, (start_date, end_date))
        
    def clear_all_attendance_history(self):
        return self.execute("DELETE FROM eventos_asistencia;")

    def get_menu_with_categories(self):
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
                "destino": cat.get('destino', 'cocina'), 
                "items": items_por_categoria.get(cat['id_categoria'], [])
            })
        return menu_completo

    def get_available_menu_items(self):
        rows = self.fetchall("SELECT id_item FROM menu_items WHERE disponible = 1;")
        return {row['id_item'] for row in rows}

    def update_menu_item_availability(self, item_id, is_available):
        return self.execute("UPDATE menu_items SET disponible = ? WHERE id_item = ?;", (int(is_available), item_id))

    def get_last_attendance_event(self, employee_id):
        return self.fetchone("SELECT tipo, timestamp FROM eventos_asistencia WHERE id_empleado = ? ORDER BY timestamp DESC LIMIT 1;", (employee_id,))

    def get_first_unlinked_employee(self):
        return self.fetchone("SELECT * FROM empleados WHERE deviceId IS NULL OR deviceId = '' ORDER BY nombre LIMIT 1;")

    def get_sales_report(self, date_str):
        total_query = """
        SELECT SUM(d.cantidad * d.precio_unitario_congelado) AS total
        FROM ordenes o
        JOIN orden_detalle d ON o.id_orden = d.id_orden
        WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) = DATE(?);
        """
        total_result = self.fetchone(total_query, (date_str,))
        total_ventas = total_result['total'] if total_result and total_result['total'] else 0.0

        items_query = """
        SELECT id_item, nombre, SUM(cant) AS cantidad_total
        FROM (
            SELECT d.id_item_menu AS id_item, m.nombre, d.cantidad AS cant
            FROM ordenes o
            JOIN orden_detalle d ON o.id_orden = d.id_orden
            JOIN menu_items m ON d.id_item_menu = m.id_item
            WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) = DATE(?)
            
            UNION ALL
            
            SELECT d.id_cerveza AS id_item, d.nombre_cerveza AS nombre, d.cantidad AS cant
            FROM ordenes o
            JOIN orden_detalle d ON o.id_orden = d.id_orden
            WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) = DATE(?) AND d.id_cerveza IS NOT NULL
        ) t
        GROUP BY id_item, nombre
        ORDER BY cantidad_total DESC;
        """
        items_vendidos = self.fetchall(items_query, (date_str, date_str))
        return total_ventas, items_vendidos
    
    def get_sales_history_range(self, start_date=None, end_date=None, days=30):
        conn = self.get_conn()
        cursor = conn.cursor()
        
        try:
            if not end_date:
                end_date_obj = datetime.date.today()
            else:
                s_end = str(end_date).strip()
                end_date_obj = datetime.datetime.strptime(s_end, '%Y-%m-%d').date()

            if not start_date:
                start_date_obj = end_date_obj - datetime.timedelta(days=days)
            else:
                s_start = str(start_date).strip()
                start_date_obj = datetime.datetime.strptime(s_start, '%Y-%m-%d').date()
            
            query = """
            SELECT 
                DATE(o.fecha_cierre) as fecha, 
                SUM(d.cantidad * d.precio_unitario_congelado) as total_dia
            FROM ordenes o
            JOIN orden_detalle d ON o.id_orden = d.id_orden
            WHERE o.estado = 'cerrada' 
            AND DATE(o.fecha_cierre) BETWEEN DATE(?) AND DATE(?)
            GROUP BY DATE(o.fecha_cierre)
            ORDER BY fecha ASC;
            """
            
            cursor.execute(query, (start_date_obj.isoformat(), end_date_obj.isoformat()))
            rows = cursor.fetchall()
            
            fechas = [row['fecha'] for row in rows]
            totales = [row['total_dia'] for row in rows]
            
            return {"fechas": fechas, "totales": totales}

        except ValueError as e:
            logger.error(f"Error de formato de fecha en historial de ventas: {e}")
            return {"fechas": [], "totales": []}
        except Exception as e:
            logger.error(f"Error general en historial de ventas: {e}")
            return {"fechas": [], "totales": []}

    def add_attendance_events_batch(self, events_list):
        query = "INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES (?, ?, ?);"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.executemany(query, events_list)
            conn.commit()
            return True
        except sqlite3.Error as e: 
            logger.error(f"Error insertando eventos de asistencia en bloque: {e}")
            return False
    
    def get_events_for_today(self):
        today_str = datetime.date.today().isoformat()
        query = """
        SELECT id_empleado, tipo, MAX(timestamp) as last_timestamp
        FROM eventos_asistencia
        WHERE DATE(timestamp) = DATE(?)
        GROUP BY id_empleado, tipo
        ORDER BY last_timestamp;
        """
        return self.fetchall(query, (today_str,))
    
    def check_duplicate_order_id(self, client_uuid):
        return self.fetchone("SELECT id_orden FROM ordenes WHERE client_uuid = ?;", (client_uuid,)) is not None

    def _get_destinations_map(self, item_ids):
        if not item_ids:
            return {}
            
        placeholders = ','.join('?' * len(item_ids))
        query = f"""
        SELECT i.id_item, c.destino
        FROM menu_items i
        JOIN menu_categorias c ON i.id_categoria = c.id_categoria
        WHERE i.id_item IN ({placeholders})
        """
        rows = self.fetchall(query, tuple(item_ids))
        return {row['id_item']: row['destino'] for row in rows}

    def create_new_order(self, orden_completa):
        conn = self.get_conn()
        
        try:
            cursor = conn.cursor()
            
            mesa_principal = str(orden_completa['numero_mesa'])
            mesas_enlazadas = orden_completa.get('mesas_enlazadas', [])
            
            mesa_key = mesa_principal
            if mesas_enlazadas:
                todas = [mesa_principal] + [str(m) for m in mesas_enlazadas]
                mesa_key = "+".join(sorted(todas))

            timestamp = orden_completa.get('timestamp', datetime.datetime.now().isoformat())
            client_uuid = orden_completa.get('order_id')
            
            cursor.execute(
                "INSERT INTO ordenes (mesa_key, estado, fecha_apertura, client_uuid, proformas_impresas) VALUES (?, 'activa', ?, ?, 0);",
                (mesa_key, timestamp, client_uuid)
            )
            id_orden = cursor.lastrowid
            
            items_data = orden_completa.get('items', [])
            item_ids = [item.get('item_id') for item in items_data]
            
            destinos_map = self._get_destinations_map(item_ids)

            detalle_batch = []
            for item in items_data:
                item_id = item.get('item_id')
                destino = destinos_map.get(item_id, 'cocina') 
                
                detalle_batch.append((
                    id_orden,
                    item_id,
                    item.get('cantidad'),
                    item.get('precio_unitario'),
                    item.get('nombre'),
                    item.get('imagen'),
                    item.get('notas', ''),
                    destino,
                    item.get('id_cerveza'),
                    item.get('nombre_cerveza') 
                ))
            cursor.executemany(
                """
                INSERT INTO orden_detalle (
                    id_orden, id_item_menu, cantidad, precio_unitario_congelado,
                    nombre_congelado, imagen_congelada, notas, destino, id_cerveza, nombre_cerveza
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                detalle_batch
            )
            
            for item in items_data:
                item_id = item.get('item_id')
                cantidad = item.get('cantidad')
                cursor.execute(
                    "UPDATE inventario SET cantidad = cantidad - ? WHERE id_menu_vinculado = ? AND es_automatico = 1;",
                    (cantidad, item_id)
                )

            conn.commit()
            logger.info(f"Orden {id_orden} creada exitosamente (Atomicidad garantizada).")
            return id_orden
            
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error CRITICO creando orden. Se hizo ROLLBACK. Causa: {e}")
            return None
        except Exception as e:
            conn.rollback()
            logger.error(f"Error logico creando orden. Rollback ejecutado. Causa: {e}")
            return None

    def get_active_orders_caja(self):
        query = """
        SELECT
            o.id_orden, o.mesa_key, o.fecha_apertura,
            d.id_detalle,
            d.cantidad, d.precio_unitario_congelado AS precio_unitario,
            d.nombre_congelado AS nombre, d.imagen_congelada AS imagen,
            d.notas, d.id_item_menu AS item_id,
            d.estado_item, d.nombre_cerveza
        FROM ordenes o
        LEFT JOIN orden_detalle d ON o.id_orden = d.id_orden
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
            
            if row['id_detalle'] is not None:
                item_dict = {
                    'id_detalle': row['id_detalle'],
                    'item_id': row['item_id'],
                    'nombre': row['nombre'],
                    'cantidad': row['cantidad'],
                    'precio_unitario': row['precio_unitario'],
                    'imagen': row['imagen'],
                    'notas': row['notas'],
                    'estado_item': row['estado_item'],
                    'nombre_cerveza': row['nombre_cerveza']
                }
                caja_data[mesa_key]['items'].append(item_dict)
                
        return caja_data

    def registrar_impresion_proforma(self, mesa_key):
        return self.execute(
            "UPDATE ordenes SET proformas_impresas = proformas_impresas + 1 WHERE mesa_key = ? AND estado = 'activa';",
            (mesa_key,)
        )
    
    def split_order(self, original_mesa_key, items_to_split, target_account_key=None, new_account_name=None):
        conn = self.get_conn()
        cursor = conn.cursor()
        
        try:
            orden_orig = self.fetchone("SELECT id_orden, client_uuid FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (original_mesa_key,))
            if not orden_orig: return False
            
            id_orden_origen = orden_orig['id_orden']
            
            temp_key = original_mesa_key.split('+')[0] if '+' in original_mesa_key else original_mesa_key
            base_mesa_key = temp_key.split('-')[0] if '-' in temp_key else temp_key

            id_destino = None

            if target_account_key:
                dest_order = self.fetchone("SELECT id_orden FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (target_account_key,))
                if dest_order:
                    id_destino = dest_order['id_orden']
            
            if not id_destino:
                if new_account_name:
                    new_mesa_key = f"{base_mesa_key}-{new_account_name}"
                else:
                    rows = self.fetchall("SELECT mesa_key FROM ordenes WHERE mesa_key LIKE ? AND estado = 'activa'", (f"{base_mesa_key}-%",))
                    
                    existing_indexes = []
                    for r in rows:
                        try:
                            parts = r['mesa_key'].split('-')
                            if len(parts) > 1 and parts[-1].isdigit():
                                existing_indexes.append(int(parts[-1]))
                        except ValueError: continue
                    
                    next_index = max(existing_indexes) + 1 if existing_indexes else 1
                    new_mesa_key = f"{base_mesa_key}-{next_index}"
                    
                    if new_mesa_key == original_mesa_key:
                        next_index += 1
                        new_mesa_key = f"{base_mesa_key}-{next_index}"
                
                new_uuid = f"{orden_orig['client_uuid']}_split_{datetime.datetime.now().timestamp()}"
                cursor.execute(
                    "INSERT INTO ordenes (mesa_key, estado, fecha_apertura, client_uuid, proformas_impresas) VALUES (?, 'activa', ?, ?, 0)",
                    (new_mesa_key, datetime.datetime.now().isoformat(), new_uuid)
                )
                id_destino = cursor.lastrowid
            
            for item in items_to_split:
                id_detalle = item.get('id') or item.get('id_detalle')
                qty_split = int(item['cantidad'])
                
                row = self.fetchone("SELECT * FROM orden_detalle WHERE id_detalle = ?", (id_detalle,))
                if not row or row['cantidad'] < qty_split: continue
                
                if row['cantidad'] == qty_split:
                    cursor.execute("UPDATE orden_detalle SET id_orden = ? WHERE id_detalle = ?", (id_destino, id_detalle))
                else:
                    cursor.execute("UPDATE orden_detalle SET cantidad = cantidad - ? WHERE id_detalle = ?", (qty_split, id_detalle))
                    cursor.execute("""
                        INSERT INTO orden_detalle (id_orden, id_item_menu, cantidad, precio_unitario_congelado, nombre_congelado, imagen_congelada, notas, destino, estado_item)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (id_destino, row['id_item_menu'], qty_split, row['precio_unitario_congelado'], row['nombre_congelado'], row['imagen_congelada'], row.get('notas', ''), row['destino'], row['estado_item']))
            
            if '-' in original_mesa_key:
                cursor.execute("SELECT COUNT(*) FROM orden_detalle WHERE id_orden = ?", (id_orden_origen,))
                remaining = cursor.fetchone()[0]
                if remaining == 0:
                    cursor.execute("UPDATE ordenes SET estado = 'cancelada', fecha_cierre = ? WHERE id_orden = ?", 
                                (datetime.datetime.now().isoformat(), id_orden_origen))

            conn.commit()
            
            self._cleanup_empty_order(original_mesa_key, id_orden_origen)
            
            return True
            
        except sqlite3.Error:
            conn.rollback()
            return False
        
    def remove_items_from_order(self, mesa_key, items_to_remove):
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            orden = self.fetchone("SELECT id_orden FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (mesa_key,))
            if not orden: return False

            id_orden = orden['id_orden']
            
            for item in items_to_remove:
                id_detalle = item['id_detalle']
                qty_to_remove = int(item['cantidad'])

                row = self.fetchone("SELECT * FROM orden_detalle WHERE id_detalle = ? AND id_orden = ? AND estado_item = 'pendiente'", (id_detalle, id_orden))
                if not row: continue 

                if row['cantidad'] <= qty_to_remove:
                    cursor.execute("DELETE FROM orden_detalle WHERE id_detalle = ?", (id_detalle,))
                else:
                    cursor.execute("UPDATE orden_detalle SET cantidad = cantidad - ? WHERE id_detalle = ?", (qty_to_remove, id_detalle))

                cursor.execute(
                    "UPDATE inventario SET cantidad = cantidad + ? WHERE id_menu_vinculado = ? AND es_automatico = 1;",
                    (qty_to_remove, row['id_item_menu'])
                )

            conn.commit()
            
            self._cleanup_empty_order(mesa_key, id_orden)

            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error removiendo items: {e}")
            return False
        
    def _cleanup_empty_order(self, mesa_key, id_orden):
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM orden_detalle WHERE id_orden = ?", (id_orden,))
            remaining = cursor.fetchone()[0]

            if remaining == 0:
                if '+' in mesa_key:
                    logger.info(f"Grupo {mesa_key} quedo vacio, pero se mantiene activo para preservar union.")
                    return False

                logger.info(f"Limpieza automatica: Orden {mesa_key} vacia. Cerrando...")
                timestamp = datetime.datetime.now().isoformat()
                cursor.execute(
                    "UPDATE ordenes SET estado = 'cancelada', fecha_cierre = ? WHERE id_orden = ?", 
                    (timestamp, id_orden)
                )
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error en limpieza automatica: {e}")
        
        return False    
    
    def _get_active_orders_by_destino(self, destino_busqueda):
        query = """
        SELECT
            o.mesa_key,
            o.fecha_apertura, 
            d.nombre_congelado AS nombre,
            d.cantidad,
            d.notas,
            d.imagen_congelada AS imagen,
            d.nombre_cerveza
        FROM ordenes o
        JOIN orden_detalle d ON o.id_orden = d.id_orden
        WHERE o.estado = 'activa'
        AND d.destino = ?
        AND d.estado_item = 'pendiente'
        ORDER BY o.fecha_apertura;
        """
        rows = self.fetchall(query, (destino_busqueda,))
        
        ordenes_dict = {}
        for item in rows:
            mesa_key = item['mesa_key']
            if mesa_key not in ordenes_dict:
                ordenes_dict[mesa_key] = {
                    'numero_mesa': mesa_key, 
                    'timestamp': item['fecha_apertura'],
                    'items': []
                }
            item_ticket = {
                'nombre': item['nombre'],
                'cantidad': item['cantidad'],
                'notas': item['notas'],
                'imagen': item['imagen'],
                'nombre_cerveza': item['nombre_cerveza']
            }
            ordenes_dict[mesa_key]['items'].append(item_ticket)
        return list(ordenes_dict.values())

    def get_active_cocina_orders(self):
        return self._get_active_orders_by_destino('cocina')
        
    def get_active_barra_orders(self):
        return self._get_active_orders_by_destino('barra')

    def _mark_order_items_ready(self, mesa_key, destino_busqueda):
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
        return self._mark_order_items_ready(mesa_key, 'cocina')
        
    def mark_barra_order_ready(self, mesa_key):
        return self._mark_order_items_ready(mesa_key, 'barra')
    
    def cancel_order_by_key(self, mesa_key):
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            orden = self.fetchone("SELECT id_orden FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (mesa_key,))
            if not orden: 
                return False

            id_orden = orden['id_orden']
            timestamp = datetime.datetime.now().isoformat()
            
            cursor.execute(
                "UPDATE orden_detalle SET estado_item = 'cancelado' WHERE id_orden = ?",
                (id_orden,)
            )
            
            cursor.execute(
                "UPDATE ordenes SET estado = 'cancelada', fecha_cierre = ? WHERE id_orden = ?", 
                (timestamp, id_orden)
            )

            cursor.execute("SELECT id_item_menu, cantidad FROM orden_detalle WHERE id_orden = ?", (id_orden,))
            items_cancelados = cursor.fetchall()
            for item in items_cancelados:
                cursor.execute(
                    "UPDATE inventario SET cantidad = cantidad + ? WHERE id_menu_vinculado = ? AND es_automatico = 1;",
                    (item['cantidad'], item['id_item_menu'])
                )
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error cancelando orden: {e}")
            return False

    def complete_order(self, mesa_key):
        orden_a_cerrar = self.get_active_orders_caja().get(mesa_key)
        if not orden_a_cerrar:
            return None
            
        timestamp = datetime.datetime.now().isoformat()
        
        self.execute("UPDATE ordenes SET estado = 'cerrada', fecha_cierre = ? WHERE mesa_key = ? AND estado = 'activa';", (timestamp, mesa_key))
        
        if '-' in mesa_key:
            try:
                base_key = mesa_key.rsplit('-', 1)[0]
                
                query_splits = "SELECT COUNT(*) as count FROM ordenes WHERE mesa_key LIKE ? AND estado = 'activa'"
                otros_splits = self.fetchone(query_splits, (f"{base_key}-%",))
                
                if otros_splits and otros_splits['count'] == 0:
                    
                    query_madre = "SELECT id_orden, mesa_key FROM ordenes WHERE (mesa_key = ? OR mesa_key LIKE ?) AND estado = 'activa'"
                    orden_madre = self.fetchone(query_madre, (base_key, f"{base_key}+%"))
                    
                    if orden_madre:
                        query_items = "SELECT COUNT(*) as count FROM orden_detalle WHERE id_orden = ?"
                        items_madre = self.fetchone(query_items, (orden_madre['id_orden'],))
                        
                        if items_madre and items_madre['count'] == 0:
                            self.execute(
                                "UPDATE ordenes SET estado = 'cerrada', fecha_cierre = ? WHERE id_orden = ?",
                                (timestamp, orden_madre['id_orden'])
                            )
                            
            except Exception as e:
                pass

        return orden_a_cerrar
    
    def get_top_products_range(self, start_date=None, end_date=None):
        conn = self.get_conn()
        cursor = conn.cursor()
        
        if not end_date:
            end_date_obj = datetime.date.today()
        else:
            end_date_obj = datetime.datetime.strptime(str(end_date).strip(), '%Y-%m-%d').date()

        if not start_date:
            start_date_obj = end_date_obj 
        else:
            start_date_obj = datetime.datetime.strptime(str(start_date).strip(), '%Y-%m-%d').date()

        query = """
        SELECT nombre, SUM(cant) AS cantidad_total
        FROM (
            SELECT m.nombre, d.cantidad AS cant
            FROM ordenes o
            JOIN orden_detalle d ON o.id_orden = d.id_orden
            JOIN menu_items m ON d.id_item_menu = m.id_item
            WHERE o.estado = 'cerrada' 
            AND DATE(o.fecha_cierre) BETWEEN DATE(?) AND DATE(?)
            
            UNION ALL
            
            SELECT d.nombre_cerveza AS nombre, d.cantidad AS cant
            FROM ordenes o
            JOIN orden_detalle d ON o.id_orden = d.id_orden
            WHERE o.estado = 'cerrada' 
            AND DATE(o.fecha_cierre) BETWEEN DATE(?) AND DATE(?)
            AND d.id_cerveza IS NOT NULL
        ) t
        GROUP BY nombre
        ORDER BY cantidad_total DESC
        LIMIT 5;
        """
        
        cursor.execute(query, (start_date_obj.isoformat(), end_date_obj.isoformat(), start_date_obj.isoformat(), end_date_obj.isoformat()))
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def update_item_note(self, id_detalle, nota):
        try:
            self.execute("UPDATE orden_detalle SET notas = ? WHERE id_detalle = ?", (nota, id_detalle))
            return True
        except Exception as e:
            logger.error(f"Error actualizando nota: {e}")
            return False

    def ensure_promo_category(self):
        self.execute("INSERT OR IGNORE INTO menu_categorias (nombre, destino) VALUES ('Promociones', 'cocina')")
        cat = self.fetchone("SELECT id_categoria FROM menu_categorias WHERE nombre = 'Promociones'")
        return cat['id_categoria'] if cat else None

    def create_combo_item(self, nombre, precio, descripcion_contenido, imagen_path):
        id_cat = self.ensure_promo_category()
        new_id = f"COMBO_{str(uuid.uuid4())[:6]}"
        
        return self.execute(
            """INSERT INTO menu_items 
               (id_item, id_categoria, nombre, precio, descripcion, imagen, disponible)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (new_id, id_cat, nombre, precio, descripcion_contenido, imagen_path)
        )