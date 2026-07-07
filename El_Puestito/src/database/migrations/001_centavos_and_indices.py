import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.database.connection import db_manager
from logger_setup import setup_logger

logger = setup_logger()

def run_migration():
    logger.info("Iniciando migración monetaria (REAL a INTEGER centavos) e índices...")
    conn = db_manager.get_conn()
    cursor = conn.cursor()
    
    try:
        # Check if already migrated
        cursor.execute("PRAGMA user_version;")
        version = cursor.fetchone()[0]
        if version >= 1:
            logger.info("Migración ya ejecutada anteriormente. Omitiendo.")
            return True
            
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Update menu_items (precio, precio_michelada) to centavos
        logger.info("Actualizando precios de menu_items a centavos...")
        cursor.execute("UPDATE menu_items SET precio = CAST(ROUND(precio * 100) AS INTEGER), precio_michelada = CAST(ROUND(precio_michelada * 100) AS INTEGER);")
        
        # 2. Update orden_detalle (precio_unitario_congelado) to centavos
        logger.info("Actualizando precios de orden_detalle a centavos...")
        cursor.execute("UPDATE orden_detalle SET precio_unitario_congelado = CAST(ROUND(precio_unitario_congelado * 100) AS INTEGER);")
        
        # 3. Create indices for performance
        logger.info("Creando índices para reportes y KDS...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_fecha_cierre ON ordenes(fecha_cierre);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_estado ON ordenes(estado);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orden_detalle_id_orden ON orden_detalle(id_orden);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orden_detalle_estado_item ON orden_detalle(estado_item);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_eventos_timestamp ON eventos_asistencia(timestamp);")
        
        # 4. Update PRAGMA user_version
        cursor.execute("PRAGMA user_version = 1;")
        
        conn.commit()
        logger.info("Migración completada exitosamente.")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error en migración, rollback ejecutado: {e}")
        return False

if __name__ == "__main__":
    run_migration()
