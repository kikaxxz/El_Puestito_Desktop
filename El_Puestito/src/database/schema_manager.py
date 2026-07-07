import os
import json
from src.database.connection import db_manager
from logger_setup import setup_logger
from src.path_manager import get_asset_path

logger = setup_logger()
JSON_ASSETS_DIR = get_asset_path("")

class SchemaManager:
    def __init__(self):
        self.initialize_schema()

    def initialize_schema(self):
        self.create_tables()
        self._check_and_update_schema()
        self._clean_orphans()
        self.run_migration_if_needed()

    def create_tables(self):
        logger.info("Verificando tablas de la base de datos...")
        db_manager.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id_empleado TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            rol TEXT,
            deviceId TEXT UNIQUE,
            fingerprint_id INTEGER UNIQUE,
            fcm_token TEXT,
            recibe_alertas INTEGER DEFAULT 1
        );
        """)

        db_manager.execute("""
        CREATE TABLE IF NOT EXISTS menu_categorias (
            id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            destino TEXT DEFAULT 'cocina' 
        );
        """)
        
        db_manager.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id_item TEXT PRIMARY KEY,
            id_categoria INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio INTEGER NOT NULL,
            precio_michelada INTEGER DEFAULT 0,
            imagen TEXT,
            disponible INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (id_categoria) REFERENCES menu_categorias (id_categoria)
        );
        """)

        db_manager.execute("""
        CREATE TABLE IF NOT EXISTS eventos_asistencia (
            id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_empleado TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            tipo TEXT NOT NULL,
            FOREIGN KEY (id_empleado) REFERENCES empleados (id_empleado)
        );
        """)

        db_manager.execute("""
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

        db_manager.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id_inventario INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            cantidad INTEGER NOT NULL DEFAULT 0,
            es_automatico INTEGER NOT NULL DEFAULT 0,
            id_menu_vinculado TEXT UNIQUE,
            FOREIGN KEY (id_menu_vinculado) REFERENCES menu_items (id_item)
        );
        """)

        db_manager.execute("""
        CREATE TABLE IF NOT EXISTS orden_detalle (
            id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
            id_orden INTEGER NOT NULL,
            id_item_menu TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario_congelado INTEGER NOT NULL,
            nombre_congelado TEXT NOT NULL,
            imagen_congelada TEXT,
            notas TEXT,
            destino TEXT NOT NULL,
            estado_item TEXT NOT NULL DEFAULT 'pendiente',
            id_cerveza TEXT,
            nombre_cerveza TEXT,
            FOREIGN KEY (id_orden) REFERENCES ordenes (id_orden),
            FOREIGN KEY (id_item_menu) REFERENCES menu_items (id_item)
        );
        """)

    def _check_and_update_schema(self):
        try:
            conn = db_manager.get_conn()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(menu_items)")
            columns_menu = [info[1] for info in cursor.fetchall()]
            if 'precio_michelada' not in columns_menu:
                logger.info("Migracion de esquema: Agregando columna precio_michelada en menu_items")
                db_manager.execute("ALTER TABLE menu_items ADD COLUMN precio_michelada INTEGER DEFAULT 0;")

            cursor.execute("PRAGMA table_info(orden_detalle)")
            columns_det = [info[1] for info in cursor.fetchall()]
            
            if 'id_cerveza' not in columns_det:
                db_manager.execute("ALTER TABLE orden_detalle ADD COLUMN id_cerveza TEXT;")
                db_manager.execute("ALTER TABLE orden_detalle ADD COLUMN nombre_cerveza TEXT;")
            
            cursor.execute("PRAGMA table_info(menu_categorias)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'destino' not in columns:
                logger.info("Migracion de esquema: Falta columna destino en menu_categorias.")
                db_manager.execute("ALTER TABLE menu_categorias ADD COLUMN destino TEXT DEFAULT 'cocina';")
                self._migrate_hardcoded_destinations_to_db()

            cursor.execute("PRAGMA table_info(empleados)")
            columns_emp = [info[1] for info in cursor.fetchall()]
            
            if 'fingerprint_id' not in columns_emp:
                logger.info("Migracion de esquema: Agregando fingerprint_id en empleados.")
                db_manager.execute("ALTER TABLE empleados ADD COLUMN fingerprint_id INTEGER;")
                db_manager.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_empleados_fingerprint ON empleados(fingerprint_id);")
                
            if 'fcm_token' not in columns_emp:
                db_manager.execute("ALTER TABLE empleados ADD COLUMN fcm_token TEXT;")
                
            if 'recibe_alertas' not in columns_emp:
                db_manager.execute("ALTER TABLE empleados ADD COLUMN recibe_alertas INTEGER DEFAULT 1;")
                
            cursor.execute("PRAGMA table_info(ordenes)")
            columns_ordenes = [info[1] for info in cursor.fetchall()]
            
            if 'proformas_impresas' not in columns_ordenes:
                logger.info("Migracion de esquema: Agregando proformas_impresas en ordenes.")
                db_manager.execute("ALTER TABLE ordenes ADD COLUMN proformas_impresas INTEGER NOT NULL DEFAULT 0;")

        except Exception as e:
            logger.error(f"Error verificando o actualizando esquema: {e}")

    def _clean_orphans(self):
        try:
            conn = db_manager.get_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM eventos_asistencia WHERE id_empleado NOT IN (SELECT id_empleado FROM empleados);")
            cursor.execute("DELETE FROM orden_detalle WHERE id_orden NOT IN (SELECT id_orden FROM ordenes);")
            conn.commit()
            logger.info("Datos huerfanos limpiados correctamente.")
        except Exception as e:
            logger.error(f"Error limpiando huerfanos: {e}")

    def _migrate_hardcoded_destinations_to_db(self):
        PREFIJOS_ANTIGUOS = ("MIC", "OBA", "BSA", "CER", "RTD")
        logger.info("Migrando logica de prefijos a base de datos...")
        categorias = db_manager.fetchall("SELECT id_categoria, nombre FROM menu_categorias")
        
        for cat in categorias:
            cat_id = cat['id_categoria']
            query_items = "SELECT id_item FROM menu_items WHERE id_categoria = ?"
            items = db_manager.fetchall(query_items, (cat_id,))
            
            es_barra = False
            for item in items:
                item_id = item['id_item']
                if any(item_id.startswith(p) for p in PREFIJOS_ANTIGUOS):
                    es_barra = True
                    break
            
            if es_barra:
                logger.info(f"Categoria '{cat['nombre']}' detectada como BARRA. Actualizando BD.")
                db_manager.execute("UPDATE menu_categorias SET destino = 'barra' WHERE id_categoria = ?", (cat_id,))

    def run_migration_if_needed(self):
        if not db_manager.fetchone("SELECT id_empleado FROM empleados LIMIT 1"):
            logger.info("Base de datos vacia detectada. Iniciando migracion de datos desde JSON...")
            self._migrate_employees()
            self._migrate_attendance_history()
            self._migrate_menu()
            logger.info("Migracion de datos completada.")
        else:
            logger.info("Base de datos ya poblada. No se requiere migracion inicial.")

    def _migrate_employees(self):
        json_path = os.path.join(JSON_ASSETS_DIR, "asistencia.json")
        try:
            with open(json_path, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            for emp in data:
                db_manager.execute(
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
                db_manager.execute(
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
                
                db_manager.execute("INSERT OR IGNORE INTO menu_categorias (nombre, destino) VALUES (?, 'cocina')", (cat_nombre,))
                cat_db = db_manager.fetchone("SELECT id_categoria FROM menu_categorias WHERE nombre = ?", (cat_nombre,))
                cat_id = cat_db['id_categoria']
                
                for item in cat.get('items', []):
                    db_manager.execute(
                        """
                        INSERT OR IGNORE INTO menu_items 
                        (id_item, id_categoria, nombre, descripcion, precio, precio_michelada, imagen, disponible)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.get('id'), cat_id, item.get('nombre'),
                            item.get('descripcion'),
                            int(item.get('precio', 0) * 100), 
                            int(item.get('precio_michelada', 0.0) * 100), 
                            item.get('imagen'),
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
