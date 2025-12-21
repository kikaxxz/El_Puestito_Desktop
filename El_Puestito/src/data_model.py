import sqlite3
import os
import threading
import json
import datetime
from logger_setup import setup_logger
logger = setup_logger()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "assets", "puestito.db")
JSON_ASSETS_DIR = os.path.join(BASE_DIR, "assets")

class DataManager:
    """
    Gestor de datos refactorizado (Paso 2 - Versión Completa).
    - Incluye migración automática de esquema (columna 'destino').
    - Elimina lógica hardcoded de prefijos de bebidas.
    - Contiene lógica completa de migración desde JSON para instalaciones nuevas.
    """

    def __init__(self, db_path):
        self.db_path = db_path
        self.local = threading.local()
        print(f"DataManager inicializado. Conectando a: {self.db_path}")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")

        self.create_tables()
        self._check_and_update_schema()
        self.run_migration_if_needed()

    def get_conn(self):
        """Obtiene o crea una conexión a la BD para el hilo actual."""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
            self.local.conn.execute("PRAGMA busy_timeout = 30000;") 
        return self.local.conn

    def close_conn_for_thread(self):
        """Cierra la conexión para el hilo actual."""
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
            logger.error(f"Error en DataManager.execute: {e}\nQuery: {query}")
            return None

    def fetchone(self, query, params=()):
        """Busca un solo registro."""
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"Error en DataManager.fetchone: {e}\nQuery: {query}")
            return None

    def fetchall(self, query, params=()):
        """Busca todos los registros que coinciden."""
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"Error en DataManager.fetchall: {e}\nQuery: {query}")
            return []

    def create_tables(self):
        """Crea la estructura base si no existe."""
        print("Verificando tablas...")
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

    def _check_and_update_schema(self):
        """
        Verifica si la BD existente necesita actualizaciones de estructura.
        Esto permite actualizar el código sin borrar la base de datos.
        """
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA table_info(menu_categorias)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'destino' not in columns:
                print("Esquema desactualizado detectado: Falta columna 'destino' en menu_categorias.")
                print("Aplicando migración de esquema...")
                
                self.execute("ALTER TABLE menu_categorias ADD COLUMN destino TEXT DEFAULT 'cocina';")
                
                self._migrate_hardcoded_destinations_to_db()
                
                print("Esquema actualizado y destinos migrados exitosamente.")

            cursor.execute("PRAGMA table_info(empleados)")
            columns_emp = [info[1] for info in cursor.fetchall()]
            
            if 'fingerprint_id' not in columns_emp:
                logger.info("Esquema: Falta columna 'fingerprint_id' en empleados. Agregando...")
                self.execute("ALTER TABLE empleados ADD COLUMN fingerprint_id INTEGER;")
                self.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_empleados_fingerprint ON empleados(fingerprint_id);")
                logger.info("Columna 'fingerprint_id' agregada correctamente.")

        except Exception as e:
            print(f"Error verificando/actualizando esquema: {e}")

    def link_fingerprint_to_employee(self, employee_id, fingerprint_id):
        """Asocia un ID de huella del sensor a un empleado."""
        try:
            self.execute("UPDATE empleados SET fingerprint_id = NULL WHERE fingerprint_id = ?", (fingerprint_id,))
            return self.execute("UPDATE empleados SET fingerprint_id = ? WHERE id_empleado = ?", (fingerprint_id, employee_id))
        except Exception as e:
            logger.error(f"Error vinculando huella: {e}")
            return False
            
    def get_employee_by_fingerprint(self, fingerprint_id):
        return self.fetchone("SELECT * FROM empleados WHERE fingerprint_id = ?", (fingerprint_id,))

    def _migrate_hardcoded_destinations_to_db(self):
        """
        Usa la antigua lista de prefijos para categorizar 
        automáticamente las categorías existentes como 'barra'.
        """
        PREFIJOS_ANTIGUOS = ("MIC", "OBA", "BSA", "CER", "RTD")
        
        print("🔄 Migrando lógica de prefijos a base de datos...")
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
                print(f"   -> Categoría '{cat['nombre']}' detectada como BARRA. Actualizando BD.")
                self.execute("UPDATE menu_categorias SET destino = 'barra' WHERE id_categoria = ?", (cat_id,))

    def run_migration_if_needed(self):
        """
        Revisa si la base de datos está vacía y, de ser así,
        importa los datos desde los archivos JSON en Assets.
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
            print(f"No se encontró {json_path} para migrar empleados.")
        except Exception as e:
            print(f"Error migrando empleados: {e}")

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
            print(f"Migrados {len(data)} eventos de asistencia desde {json_path}")
        except FileNotFoundError:
            print(f"No se encontró {json_path} para migrar historial.")
        except Exception as e:
            print(f"Error migrando historial de asistencia: {e}")

    def _migrate_menu(self):
        """Importa datos desde menu.json, asignando destino por defecto."""
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

            print(f"Migrados {item_count} items de menú desde {json_path}")
        except FileNotFoundError:
            print(f"No se encontró {json_path} para migrar menú.")
        except Exception as e:
            print(f"Error migrando menú: {e}")


    def get_employees(self):
        return self.fetchall("SELECT * FROM empleados ORDER BY nombre;")

    def get_employee_by_id(self, employee_id):
        return self.fetchone("SELECT * FROM empleados WHERE id_empleado = ?;", (employee_id,))

    def get_employee_by_device(self, device_id):
        return self.fetchone("SELECT * FROM empleados WHERE deviceId = ?;", (device_id,))
        
    def add_employee(self, id, nombre, rol, fingerprint_id=None):
        """Ahora acepta el ID de la huella opcionalmente."""
        return self.execute(
            "INSERT INTO empleados (id_empleado, nombre, rol, fingerprint_id) VALUES (?, ?, ?, ?);", 
            (id, nombre, rol, fingerprint_id)
        )

    def update_employee(self, id_original, new_id, new_name, new_rol, fingerprint_id=None):
        """Actualiza también la huella."""
        return self.execute(
            "UPDATE empleados SET id_empleado = ?, nombre = ?, rol = ?, fingerprint_id = ? WHERE id_empleado = ?;", 
            (new_id, new_name, new_rol, fingerprint_id, id_original)
        )
        
    def delete_employee(self, employee_id):
        try:
            return self.execute("DELETE FROM empleados WHERE id_empleado = ?;", (employee_id,))
        except sqlite3.IntegrityError:
            print(f"No se puede borrar empleado {employee_id}, tiene historial.")
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
        """Retorna el menú completo incluyendo el destino de impresión."""
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
        SELECT d.id_item_menu, m.nombre, SUM(d.cantidad) AS cantidad_total
        FROM ordenes o
        JOIN orden_detalle d ON o.id_orden = d.id_orden
        JOIN menu_items m ON d.id_item_menu = m.id_item
        WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) = DATE(?)
        GROUP BY d.id_item_menu, m.nombre
        ORDER BY cantidad_total DESC;
        """
        items_vendidos = self.fetchall(items_query, (date_str,))
        return total_ventas, items_vendidos
    
    def get_sales_history_range(self, start_date=None, end_date=None, days=30):
        """
        Obtiene ventas totales por día. Versión blindada para fechas.
        """
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
            print(f"Error de formato de fecha en DataManager: {e}")
            return {"fechas": [], "totales": []}
        except Exception as e:
            print(f"Error general en historial: {e}")
            return {"fechas": [], "totales": []}

    def add_attendance_events_batch(self, events_list):
        query = "INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES (?, ?, ?);"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.executemany(query, events_list)
            conn.commit()
            return True
        except sqlite3.Error: return False
    
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
        """
        Helper eficiente para obtener el destino de múltiples items.
        Retorna un dict: { 'id_item': 'barra', 'id_item_2': 'cocina' }
        """
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
        """
        Crea una nueva orden con transacción atómica explícita.
        Si algo falla (ej: menu cambia, error de red), se deshace todo.
        """
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
                "INSERT INTO ordenes (mesa_key, estado, fecha_apertura, client_uuid) VALUES (?, 'activa', ?, ?);",
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
                    destino 
                ))
            cursor.executemany(
                """
                INSERT INTO orden_detalle (
                    id_orden, id_item_menu, cantidad, precio_unitario_congelado,
                    nombre_congelado, imagen_congelada, notas, destino
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                detalle_batch
            )
            conn.commit()
            logger.info(f"Orden {id_orden} creada exitosamente (Atomicidad garantizada).")
            return id_orden
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error CRÍTICO creando orden. Se hizo ROLLBACK. Causa: {e}")
            return None
        except Exception as e:
            conn.rollback()
            print(f"Error lógico creando orden. Rollback ejecutado. Causa: {e}")
            return None

    def get_active_orders_caja(self):
        """
        Obtiene el estado de todas las mesas activas.
        """
        query = """
        SELECT
            o.id_orden, o.mesa_key, o.fecha_apertura,
            d.id_detalle,
            d.cantidad, d.precio_unitario_congelado AS precio_unitario,
            d.nombre_congelado AS nombre, d.imagen_congelada AS imagen,
            d.notas, d.id_item_menu AS item_id,
            d.estado_item
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
                    'estado_item': row['estado_item']
                }
                caja_data[mesa_key]['items'].append(item_dict)
                
        return caja_data
    
    def split_order(self, original_mesa_key, items_to_split):
        """
        Mueve ítems de una orden activa a una nueva orden derivada.
        CORREGIDO: 
        1. Evita recursión infinita (siempre usa la mesa base).
        2. Elimina la sub-cuenta de origen si queda vacía (evita mesas fantasmas).
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        try:
            orden_orig = self.fetchone("SELECT id_orden, client_uuid FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (original_mesa_key,))
            if not orden_orig: return False
            
            id_orden_origen = orden_orig['id_orden']
            
            temp_key = original_mesa_key.split('+')[0] if '+' in original_mesa_key else original_mesa_key
            base_mesa_key = temp_key.split('-')[0] if '-' in temp_key else temp_key

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
                "INSERT INTO ordenes (mesa_key, estado, fecha_apertura, client_uuid) VALUES (?, 'activa', ?, ?)",
                (new_mesa_key, datetime.datetime.now().isoformat(), new_uuid)
            )
            id_nueva_orden = cursor.lastrowid
            
            for item in items_to_split:
                id_detalle = item['id_detalle']
                qty_split = item['cantidad']
                
                row = self.fetchone("SELECT * FROM orden_detalle WHERE id_detalle = ?", (id_detalle,))
                if not row or row['cantidad'] < qty_split: continue
                
                if row['cantidad'] == qty_split:
                    cursor.execute("UPDATE orden_detalle SET id_orden = ? WHERE id_detalle = ?", (id_nueva_orden, id_detalle))
                else:
                    cursor.execute("UPDATE orden_detalle SET cantidad = cantidad - ? WHERE id_detalle = ?", (qty_split, id_detalle))
                    cursor.execute("""
                        INSERT INTO orden_detalle (id_orden, id_item_menu, cantidad, precio_unitario_congelado, nombre_congelado, imagen_congelada, notas, destino, estado_item)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (id_nueva_orden, row['id_item_menu'], qty_split, row['precio_unitario_congelado'], row['nombre_congelado'], row['imagen_congelada'], row['notas'], row['destino'], row['estado_item']))
            
            if '-' in original_mesa_key:
                cursor.execute("SELECT COUNT(*) FROM orden_detalle WHERE id_orden = ?", (id_orden_origen,))
                remaining = cursor.fetchone()[0]
                if remaining == 0:
                    print(f"Sub-cuenta {original_mesa_key} quedó vacía tras el movimiento. Eliminando...")
                    cursor.execute("UPDATE ordenes SET estado = 'cancelada', fecha_cierre = ? WHERE id_orden = ?", 
                                (datetime.datetime.now().isoformat(), id_orden_origen))

            conn.commit()
            self._cleanup_empty_order(original_mesa_key, id_orden_origen)
            logger.info(f"Cuenta separada creada: {new_mesa_key}")
            return True
            
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error al separar cuenta (split_order): {e}")
            return False
        
    def separar_cuenta_en_mesas_unidas(self, mesa_origen_key, items_a_mover):
        """
        Versión SQLITE NATIVA para separar cuentas.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        try:
            orden_orig = self.fetchone("SELECT id_orden, client_uuid FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (mesa_origen_key,))
            if not orden_orig:
                print("No se encontró orden activa para separar.")
                return False
            
            temp_key = mesa_origen_key.split('+')[0] if '+' in mesa_origen_key else mesa_origen_key
            

            base_mesa_key = temp_key.split('-')[0] if '-' in temp_key else temp_key

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
            
            if new_mesa_key == mesa_origen_key:
                next_index += 1
                new_mesa_key = f"{base_mesa_key}-{next_index}"

            new_uuid = f"{orden_orig['client_uuid']}_split_{datetime.datetime.now().timestamp()}"
            
            cursor.execute(
                "INSERT INTO ordenes (mesa_key, estado, fecha_apertura, client_uuid) VALUES (?, 'activa', ?, ?)",
                (new_mesa_key, datetime.datetime.now().isoformat(), new_uuid)
            )
            id_nueva_orden = cursor.lastrowid
            
            for item_data in items_a_mover:
                id_detalle = item_data.get('id') or item_data.get('id_detalle')
                cantidad_a_mover = int(item_data['cantidad'])
                
                row = self.fetchone("SELECT * FROM orden_detalle WHERE id_detalle = ?", (id_detalle,))
                if not row: continue
                    
                cantidad_actual = row['cantidad']
                
                if cantidad_actual == cantidad_a_mover:
                    cursor.execute("UPDATE orden_detalle SET id_orden = ? WHERE id_detalle = ?", (id_nueva_orden, id_detalle))
                elif cantidad_actual > cantidad_a_mover:
                    cursor.execute("UPDATE orden_detalle SET cantidad = cantidad - ? WHERE id_detalle = ?", (cantidad_a_mover, id_detalle))
                    cursor.execute("""
                        INSERT INTO orden_detalle 
                        (id_orden, id_item_menu, cantidad, precio_unitario_congelado, nombre_congelado, imagen_congelada, notas, destino, estado_item)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        id_nueva_orden, row['id_item_menu'], cantidad_a_mover, row['precio_unitario_congelado'], 
                        row['nombre_congelado'], row['imagen_congelada'], row.get('notas', ''), 
                        row['destino'], row['estado_item']
                    ))

            conn.commit()
            print(f"Cuenta separada exitosamente: {new_mesa_key} (Hermana de {base_mesa_key})")
            return id_nueva_orden
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error al separar cuenta: {e}")
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

            conn.commit()
            
            self._cleanup_empty_order(mesa_key, id_orden)

            return True
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error removing items: {e}")
            return False
        
    def _cleanup_empty_order(self, mesa_key, id_orden):
        """
        Verifica si una orden quedó vacía y la cierra automáticamente si corresponde.
        Reglas:
        - Subcuentas (1-1): Se cierran.
        - Mesas simples (1): Se cierran.
        - Grupos (1+2): NO se cierran para mantener la unión visual en el mapa.
        """
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM orden_detalle WHERE id_orden = ?", (id_orden,))
            remaining = cursor.fetchone()[0]

            if remaining == 0:
                if '+' in mesa_key:
                    logger.info(f"Grupo {mesa_key} quedó vacío, pero se mantiene activo para preservar unión.")
                    return False

                logger.info(f"Limpieza automática: Orden {mesa_key} vacía. Cerrando...")
                timestamp = datetime.datetime.now().isoformat()
                cursor.execute(
                    "UPDATE ordenes SET estado = 'cancelada', fecha_cierre = ? WHERE id_orden = ?", 
                    (timestamp, id_orden)
                )
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error en limpieza automática: {e}")
        
        return False    
    
    def _get_active_orders_by_destino(self, destino_busqueda):
        query = """
        SELECT
            o.mesa_key,
            o.fecha_apertura, 
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
                'imagen': item['imagen']
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
        """
        Fuerza la cancelación de una orden específica (útil para mesas bugeadas/vacías).
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            orden = self.fetchone("SELECT id_orden FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (mesa_key,))
            if not orden: return False

            id_orden = orden['id_orden']
            
            cursor.execute("SELECT COUNT(*) FROM orden_detalle WHERE id_orden = ?", (id_orden,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"⚠️ No se puede cancelar mesa {mesa_key}, aún tiene {count} productos.")
                return False

            timestamp = datetime.datetime.now().isoformat()
            cursor.execute(
                "UPDATE ordenes SET estado = 'cancelada', fecha_cierre = ? WHERE id_orden = ?", 
                (timestamp, id_orden)
            )
            conn.commit()
            print(f"Orden {mesa_key} cancelada manualmente.")
            return True
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error cancelando orden: {e}")
            return False

    def complete_order(self, mesa_key):
        """
        Cierra una orden activa y realiza limpieza automática de 'cuentas fantasmas'.
        """
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
                            logger.info(f"Limpieza automática: Cerrando orden grupal vacía {orden_madre['mesa_key']}")
                            self.execute(
                                "UPDATE ordenes SET estado = 'cerrada', fecha_cierre = ? WHERE id_orden = ?",
                                (timestamp, orden_madre['id_orden'])
                            )
                            
            except Exception as e:
                print(f"Error en validación de limpieza automática: {e}")

        return orden_a_cerrar
    
    def get_top_products_range(self, start_date=None, end_date=None):
        """
        Obtiene los 5 productos más vendidos en un rango de fechas específico.
        """
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
        SELECT m.nombre, SUM(d.cantidad) AS cantidad_total
        FROM ordenes o
        JOIN orden_detalle d ON o.id_orden = d.id_orden
        JOIN menu_items m ON d.id_item_menu = m.id_item
        WHERE o.estado = 'cerrada' 
        AND DATE(o.fecha_cierre) BETWEEN DATE(?) AND DATE(?)
        GROUP BY d.id_item_menu, m.nombre
        ORDER BY cantidad_total DESC
        LIMIT 5;
        """
        
        cursor.execute(query, (start_date_obj.isoformat(), end_date_obj.isoformat()))
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def update_item_note(self, id_detalle, nota):
        """Actualiza la nota de un ítem específico en una orden activa."""
        try:
            self.execute("UPDATE orden_detalle SET notas = ? WHERE id_detalle = ?", (nota, id_detalle))
            return True
        except Exception as e:
            print(f"Error actualizando nota: {e}")
            return False

    def ensure_promo_category(self):
        """Asegura que exista la categoría Promociones para guardar los combos."""
        self.execute("INSERT OR IGNORE INTO menu_categorias (nombre, destino) VALUES ('Promociones', 'cocina')")
        cat = self.fetchone("SELECT id_categoria FROM menu_categorias WHERE nombre = 'Promociones'")
        return cat['id_categoria'] if cat else None

    def create_combo_item(self, nombre, precio, descripcion_contenido, imagen_path):
        """Crea el combo como un item único en el menú."""
        id_cat = self.ensure_promo_category()
        
        import uuid
        new_id = f"COMBO_{str(uuid.uuid4())[:6]}"
        
        return self.execute(
            """INSERT INTO menu_items 
               (id_item, id_categoria, nombre, precio, descripcion, imagen, disponible)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (new_id, id_cat, nombre, precio, descripcion_contenido, imagen_path)
        )