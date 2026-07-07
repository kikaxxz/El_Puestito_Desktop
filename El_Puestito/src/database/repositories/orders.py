from src.database.connection import db_manager
import sqlite3
import datetime
import uuid
from logger_setup import setup_logger

logger = setup_logger()

class OrderRepository:
    def check_duplicate_order_id(self, client_uuid):
        return db_manager.fetchone("SELECT id_orden FROM ordenes WHERE client_uuid = ?;", (client_uuid,)) is not None

    def create_new_order(self, orden_completa):
        conn = db_manager.get_conn()
        try:
            cursor = conn.cursor()
            
            target_account = orden_completa.get('target_account_key')
            new_account = orden_completa.get('new_account_name')
            
            mesa_principal = str(orden_completa['numero_mesa'])
            mesas_enlazadas = orden_completa.get('mesas_enlazadas', [])
            
            base_key = mesa_principal
            if mesas_enlazadas:
                todas = [mesa_principal] + [str(m) for m in mesas_enlazadas]
                base_key = "+".join(sorted(todas))
                
            if target_account:
                mesa_key = target_account
            elif new_account:
                mesa_key = f"{base_key}-{new_account}"
            else:
                mesa_key = base_key

            timestamp = orden_completa.get('timestamp', datetime.datetime.now().isoformat())
            client_uuid = orden_completa.get('order_id')
            
            cursor.execute(
                "INSERT INTO ordenes (mesa_key, estado, fecha_apertura, client_uuid, proformas_impresas) VALUES (?, 'activa', ?, ?, 0);",
                (mesa_key, timestamp, client_uuid)
            )
            id_orden = cursor.lastrowid
            
            items_data = orden_completa.get('items', [])
            
            detalle_batch = []
            for item in items_data:
                item_id = item.get('item_id')
                cantidad = item.get('cantidad')
                id_cerveza = item.get('id_cerveza')
                
                if not isinstance(cantidad, int) or cantidad <= 0:
                    raise ValueError(f"Cantidad invalida para el item {item_id}.")

                cursor.execute("""
                    SELECT i.id_item, i.nombre, i.precio, i.precio_michelada, c.destino, i.disponible
                    FROM menu_items i
                    JOIN menu_categorias c ON i.id_categoria = c.id_categoria
                    WHERE i.id_item = ?
                """, (item_id,))
                menu_item = cursor.fetchone()
                
                if not menu_item or not menu_item['disponible']:
                    raise ValueError(f"El producto {item_id} no existe o no esta disponible.")

                destino = menu_item['destino']
                nombre = menu_item['nombre']
                precio_unitario = menu_item['precio']

                if id_cerveza and menu_item['precio_michelada'] > 0:
                    precio_unitario = menu_item['precio_michelada']
                    
                nombre_cerveza = item.get('nombre_cerveza')

                cursor.execute("SELECT cantidad, es_automatico FROM inventario WHERE id_menu_vinculado = ?", (item_id,))
                stock_info = cursor.fetchone()
                
                if stock_info and stock_info['es_automatico']:
                    if stock_info['cantidad'] < cantidad:
                        raise ValueError(f"Stock insuficiente para {nombre}. Solicitado: {cantidad}, Disponible: {stock_info['cantidad']}")
                    
                    cursor.execute(
                        "UPDATE inventario SET cantidad = cantidad - ? WHERE id_menu_vinculado = ?",
                        (cantidad, item_id)
                    )

                detalle_batch.append((
                    id_orden, item_id, cantidad, precio_unitario, nombre,
                    item.get('imagen'), item.get('notas', ''), destino, id_cerveza, nombre_cerveza
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

            conn.commit()
            logger.info(f"Orden {id_orden} creada exitosamente (Atomicidad garantizada).")
            return id_orden
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            logger.warning(f"Error de Integridad (posible UUID duplicado): {e}")
            raise e
        except Exception as e:
            conn.rollback()
            logger.error(f"Error logico creando orden. Rollback ejecutado. Causa: {e}")
            raise e

    def get_active_orders_caja(self):
        query = """
        SELECT
            o.id_orden, o.mesa_key, o.fecha_apertura,
            d.id_detalle, d.cantidad, d.precio_unitario_congelado AS precio_unitario,
            d.nombre_congelado AS nombre, d.imagen_congelada AS imagen,
            d.notas, d.id_item_menu AS item_id, d.estado_item, d.nombre_cerveza
        FROM ordenes o
        LEFT JOIN orden_detalle d ON o.id_orden = d.id_orden
        WHERE o.estado = 'activa'
        ORDER BY o.fecha_apertura;
        """
        rows = db_manager.fetchall(query)
        
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
                    'id_detalle': row['id_detalle'], 'item_id': row['item_id'],
                    'nombre': row['nombre'], 'cantidad': row['cantidad'],
                    'precio_unitario': row['precio_unitario'] / 100.0, 'imagen': row['imagen'],
                    'notas': row['notas'], 'estado_item': row['estado_item'],
                    'nombre_cerveza': row['nombre_cerveza']
                }
                caja_data[mesa_key]['items'].append(item_dict)
        return caja_data

    def registrar_impresion_proforma(self, mesa_key):
        return db_manager.execute(
            "UPDATE ordenes SET proformas_impresas = proformas_impresas + 1 WHERE mesa_key = ? AND estado = 'activa';",
            (mesa_key,)
        )
    
    def split_order(self, original_mesa_key, items_to_split, target_account_key=None, new_account_name=None):
        conn = db_manager.get_conn()
        cursor = conn.cursor()
        
        try:
            orden_orig = db_manager.fetchone("SELECT id_orden, client_uuid FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (original_mesa_key,))
            if not orden_orig: return False
            
            id_orden_origen = orden_orig['id_orden']
            temp_key = original_mesa_key.split('+')[0] if '+' in original_mesa_key else original_mesa_key
            base_mesa_key = temp_key.split('-')[0] if '-' in temp_key else temp_key
            id_destino = None

            if target_account_key:
                dest_order = db_manager.fetchone("SELECT id_orden FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (target_account_key,))
                if dest_order: id_destino = dest_order['id_orden']
            
            if not id_destino:
                if new_account_name:
                    new_mesa_key = f"{base_mesa_key}-{new_account_name}"
                else:
                    rows = db_manager.fetchall("SELECT mesa_key FROM ordenes WHERE mesa_key LIKE ? AND estado = 'activa'", (f"{base_mesa_key}-%",))
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
                if qty_split <= 0: raise ValueError("Cantidad a separar debe ser mayor a 0")
                row = db_manager.fetchone("SELECT * FROM orden_detalle WHERE id_detalle = ? AND id_orden = ?", (id_detalle, id_orden_origen))
                if not row or row['cantidad'] < qty_split: 
                    raise ValueError(f"Item invalido o cantidad solicitada excede el actual para id_detalle {id_detalle}.")
                
                if row['cantidad'] == qty_split:
                    cursor.execute("UPDATE orden_detalle SET id_orden = ? WHERE id_detalle = ?", (id_destino, id_detalle))
                else:
                    cursor.execute("UPDATE orden_detalle SET cantidad = cantidad - ? WHERE id_detalle = ?", (qty_split, id_detalle))
                    cursor.execute("""
                        INSERT INTO orden_detalle (id_orden, id_item_menu, cantidad, precio_unitario_congelado, nombre_congelado, imagen_congelada, notas, destino, estado_item, id_cerveza, nombre_cerveza)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (id_destino, row['id_item_menu'], qty_split, row['precio_unitario_congelado'], row['nombre_congelado'], row['imagen_congelada'], row.get('notas', ''), row['destino'], row['estado_item'], row.get('id_cerveza'), row.get('nombre_cerveza')))
            
            if '-' in original_mesa_key:
                cursor.execute("SELECT COUNT(*) FROM orden_detalle WHERE id_orden = ?", (id_orden_origen,))
                remaining = cursor.fetchone()[0]
                if remaining == 0:
                    cursor.execute("UPDATE ordenes SET estado = 'cancelada', fecha_cierre = ? WHERE id_orden = ?", 
                                (datetime.datetime.now().isoformat(), id_orden_origen))

            conn.commit()
            self._cleanup_empty_order(original_mesa_key, id_orden_origen)
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error en split_order: {e}")
            return False
        
    def remove_items_from_order(self, mesa_key, items_to_remove):
        conn = db_manager.get_conn()
        cursor = conn.cursor()
        try:
            orden = db_manager.fetchone("SELECT id_orden FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (mesa_key,))
            if not orden: return False
            id_orden = orden['id_orden']
            
            for item in items_to_remove:
                id_detalle = item['id_detalle']
                qty_to_remove = int(item['cantidad'])
                if qty_to_remove <= 0: raise ValueError("La cantidad a eliminar debe ser mayor a 0")
                row = db_manager.fetchone("SELECT * FROM orden_detalle WHERE id_detalle = ? AND id_orden = ? AND estado_item = 'pendiente'", (id_detalle, id_orden))
                if not row: 
                    raise ValueError(f"Item invalido o ya procesado (id_detalle: {id_detalle}).")
                if row['cantidad'] < qty_to_remove:
                    raise ValueError(f"Cantidad a eliminar mayor a la existente para item {id_detalle}.")

                if row['cantidad'] == qty_to_remove:
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
            conn = db_manager.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM orden_detalle WHERE id_orden = ?", (id_orden,))
            remaining = cursor.fetchone()[0]
            if remaining == 0:
                if '+' in mesa_key:
                    return False
                cursor.execute("UPDATE ordenes SET estado = 'cancelada', fecha_cierre = ? WHERE id_orden = ?", 
                    (datetime.datetime.now().isoformat(), id_orden))
                conn.commit()
                return True
        except Exception as e:
            pass
        return False    
    
    def _get_active_orders_by_destino(self, destino_busqueda):
        query = """
        SELECT o.mesa_key, o.fecha_apertura, d.id_detalle, d.nombre_congelado AS nombre,
               d.cantidad, d.notas, d.imagen_congelada AS imagen, d.nombre_cerveza
        FROM ordenes o
        JOIN orden_detalle d ON o.id_orden = d.id_orden
        WHERE o.estado = 'activa' AND d.destino = ? AND d.estado_item = 'pendiente'
        ORDER BY o.fecha_apertura;
        """
        rows = db_manager.fetchall(query, (destino_busqueda,))
        ordenes_dict = {}
        for item in rows:
            mesa_key = item['mesa_key']
            if mesa_key not in ordenes_dict:
                ordenes_dict[mesa_key] = {'numero_mesa': mesa_key, 'timestamp': item['fecha_apertura'], 'items': []}
            ordenes_dict[mesa_key]['items'].append({
                'id_detalle': item['id_detalle'], 'nombre': item['nombre'],
                'cantidad': item['cantidad'], 'notas': item['notas'],
                'imagen': item['imagen'], 'nombre_cerveza': item['nombre_cerveza']
            })
        return list(ordenes_dict.values())

    def get_active_cocina_orders(self): return self._get_active_orders_by_destino('cocina')
    def get_active_barra_orders(self): return self._get_active_orders_by_destino('barra')

    def mark_individual_item_ready(self, id_detalle):
        conn = db_manager.get_conn()
        cursor = conn.cursor()
        try:
            row = db_manager.fetchone("SELECT * FROM orden_detalle WHERE id_detalle = ? AND estado_item = 'pendiente'", (id_detalle,))
            if not row: return False
            if row['cantidad'] == 1:
                cursor.execute("UPDATE orden_detalle SET estado_item = 'listo' WHERE id_detalle = ?", (id_detalle,))
            else:
                cursor.execute("UPDATE orden_detalle SET cantidad = cantidad - 1 WHERE id_detalle = ?", (id_detalle,))
                cursor.execute("""
                    INSERT INTO orden_detalle (id_orden, id_item_menu, cantidad, precio_unitario_congelado, nombre_congelado, imagen_congelada, notas, destino, estado_item, id_cerveza, nombre_cerveza)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?, 'listo', ?, ?)
                """, (row['id_orden'], row['id_item_menu'], row['precio_unitario_congelado'], row['nombre_congelado'], row['imagen_congelada'], row.get('notas', ''), row['destino'], row.get('id_cerveza'), row.get('nombre_cerveza')))
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False

    def _mark_order_items_ready(self, mesa_key, destino_busqueda):
        query = """
        UPDATE orden_detalle SET estado_item = 'listo'
        WHERE destino = ? AND estado_item = 'pendiente'
        AND id_orden IN (SELECT id_orden FROM ordenes WHERE mesa_key = ? AND estado = 'activa');
        """
        return db_manager.execute(query, (destino_busqueda, mesa_key))

    def mark_cocina_order_ready(self, mesa_key): return self._mark_order_items_ready(mesa_key, 'cocina')
    def mark_barra_order_ready(self, mesa_key): return self._mark_order_items_ready(mesa_key, 'barra')
    
    def cancel_order_by_key(self, mesa_key):
        conn = db_manager.get_conn()
        cursor = conn.cursor()
        try:
            orden = db_manager.fetchone("SELECT id_orden FROM ordenes WHERE mesa_key = ? AND estado = 'activa'", (mesa_key,))
            if not orden: return False
            id_orden = orden['id_orden']
            timestamp = datetime.datetime.now().isoformat()
            cursor.execute("UPDATE orden_detalle SET estado_item = 'cancelado' WHERE id_orden = ?", (id_orden,))
            cursor.execute("UPDATE ordenes SET estado = 'cancelada', fecha_cierre = ? WHERE id_orden = ?", (timestamp, id_orden))
            cursor.execute("SELECT id_item_menu, cantidad FROM orden_detalle WHERE id_orden = ?", (id_orden,))
            for item in cursor.fetchall():
                cursor.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE id_menu_vinculado = ? AND es_automatico = 1;", (item['cantidad'], item['id_item_menu']))
            conn.commit()
            return True
        except sqlite3.Error as e:
            conn.rollback()
            return False

    def complete_order(self, mesa_key):
        orden_a_cerrar = self.get_active_orders_caja().get(mesa_key)
        if not orden_a_cerrar: return None
        timestamp = datetime.datetime.now().isoformat()
        db_manager.execute("UPDATE ordenes SET estado = 'cerrada', fecha_cierre = ? WHERE mesa_key = ? AND estado = 'activa';", (timestamp, mesa_key))
        if '-' in mesa_key:
            try:
                base_key = mesa_key.rsplit('-', 1)[0]
                otros_splits = db_manager.fetchone("SELECT COUNT(*) as count FROM ordenes WHERE mesa_key LIKE ? AND estado = 'activa'", (f"{base_key}-%",))
                if otros_splits and otros_splits['count'] == 0:
                    orden_madre = db_manager.fetchone("SELECT id_orden, mesa_key FROM ordenes WHERE (mesa_key = ? OR mesa_key LIKE ?) AND estado = 'activa'", (base_key, f"{base_key}+%"))
                    if orden_madre:
                        items_madre = db_manager.fetchone("SELECT COUNT(*) as count FROM orden_detalle WHERE id_orden = ?", (orden_madre['id_orden'],))
                        if items_madre and items_madre['count'] == 0:
                            db_manager.execute("UPDATE ordenes SET estado = 'cerrada', fecha_cierre = ? WHERE id_orden = ?", (timestamp, orden_madre['id_orden']))
            except Exception: pass
        return orden_a_cerrar

    def update_item_note(self, id_detalle, nota):
        try:
            db_manager.execute("UPDATE orden_detalle SET notas = ? WHERE id_detalle = ?", (nota, id_detalle))
            return True
        except Exception: return False

    def get_sales_report(self, date_str):
        total_result = db_manager.fetchone("""
            SELECT SUM(d.cantidad * d.precio_unitario_congelado) AS total
            FROM ordenes o JOIN orden_detalle d ON o.id_orden = d.id_orden
            WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) = DATE(?);
        """, (date_str,))
        total_ventas = (total_result['total'] / 100.0) if total_result and total_result['total'] else 0.0

        items_vendidos = db_manager.fetchall("""
            SELECT id_item, nombre, SUM(cant) AS cantidad_total FROM (
                SELECT d.id_item_menu AS id_item, d.nombre_congelado AS nombre, d.cantidad AS cant
                FROM ordenes o JOIN orden_detalle d ON o.id_orden = d.id_orden
                WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) = DATE(?)
                UNION ALL
                SELECT d.id_cerveza AS id_item, d.nombre_cerveza AS nombre, d.cantidad AS cant
                FROM ordenes o JOIN orden_detalle d ON o.id_orden = d.id_orden
                WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) = DATE(?) AND d.id_cerveza IS NOT NULL
            ) t GROUP BY id_item, nombre ORDER BY cantidad_total DESC;
        """, (date_str, date_str))
        return total_ventas, items_vendidos
    
    def get_sales_history_range(self, start_date=None, end_date=None, days=30):
        try:
            if not end_date: end_date_obj = datetime.date.today()
            else: end_date_obj = datetime.datetime.strptime(str(end_date).strip(), '%Y-%m-%d').date()

            if not start_date: start_date_obj = end_date_obj - datetime.timedelta(days=days)
            else: start_date_obj = datetime.datetime.strptime(str(start_date).strip(), '%Y-%m-%d').date()
            
            rows = db_manager.fetchall("""
                SELECT DATE(o.fecha_cierre) as fecha, SUM(d.cantidad * d.precio_unitario_congelado) as total_dia
                FROM ordenes o JOIN orden_detalle d ON o.id_orden = d.id_orden
                WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) BETWEEN DATE(?) AND DATE(?)
                GROUP BY DATE(o.fecha_cierre) ORDER BY fecha ASC;
            """, (start_date_obj.isoformat(), end_date_obj.isoformat()))
            return {"fechas": [row['fecha'] for row in rows], "totales": [row['total_dia'] / 100.0 for row in rows]}
        except Exception:
            return {"fechas": [], "totales": []}

    def get_top_products_range(self, start_date=None, end_date=None):
        if not end_date: end_date_obj = datetime.date.today()
        else: end_date_obj = datetime.datetime.strptime(str(end_date).strip(), '%Y-%m-%d').date()

        if not start_date: start_date_obj = end_date_obj 
        else: start_date_obj = datetime.datetime.strptime(str(start_date).strip(), '%Y-%m-%d').date()

        rows = db_manager.fetchall("""
            SELECT nombre, SUM(cant) AS cantidad_total FROM (
                SELECT d.nombre_congelado AS nombre, d.cantidad AS cant FROM ordenes o JOIN orden_detalle d ON o.id_orden = d.id_orden
                WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) BETWEEN DATE(?) AND DATE(?)
                UNION ALL
                SELECT d.nombre_cerveza AS nombre, d.cantidad AS cant FROM ordenes o JOIN orden_detalle d ON o.id_orden = d.id_orden
                WHERE o.estado = 'cerrada' AND DATE(o.fecha_cierre) BETWEEN DATE(?) AND DATE(?) AND d.id_cerveza IS NOT NULL
            ) t GROUP BY nombre ORDER BY cantidad_total DESC LIMIT 5;
        """, (start_date_obj.isoformat(), end_date_obj.isoformat(), start_date_obj.isoformat(), end_date_obj.isoformat()))
        return [dict(row) for row in rows]

order_repo = OrderRepository()
