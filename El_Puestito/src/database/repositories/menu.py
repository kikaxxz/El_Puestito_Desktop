from src.database.connection import db_manager
from logger_setup import setup_logger

logger = setup_logger()

class MenuRepository:
    def get_menu_with_categories(self):
        categorias = db_manager.fetchall("SELECT * FROM menu_categorias ORDER BY nombre;")
        items = db_manager.fetchall("SELECT * FROM menu_items;")
        
        menu_completo = {"categorias": []}
        items_por_categoria = {}
        for item in items:
            item_copy = dict(item)
            if 'precio' in item_copy:
                item_copy['precio'] = item_copy['precio'] / 100.0
            if 'precio_michelada' in item_copy:
                item_copy['precio_michelada'] = item_copy['precio_michelada'] / 100.0
                
            cat_id = item_copy['id_categoria']
            if cat_id not in items_por_categoria:
                items_por_categoria[cat_id] = []
            items_por_categoria[cat_id].append(item_copy)
            
        for cat in categorias:
            menu_completo["categorias"].append({
                "nombre": cat['nombre'],
                "destino": cat.get('destino', 'cocina'), 
                "items": items_por_categoria.get(cat['id_categoria'], [])
            })
        return menu_completo

    def get_available_menu_items(self):
        rows = db_manager.fetchall("SELECT id_item FROM menu_items WHERE disponible = 1;")
        return {row['id_item'] for row in rows}

    def update_menu_item_availability(self, item_id, is_available):
        return db_manager.execute("UPDATE menu_items SET disponible = ? WHERE id_item = ?;", (int(is_available), item_id))

    def get_destinations_map(self, item_ids):
        if not item_ids:
            return {}
            
        placeholders = ','.join('?' * len(item_ids))
        query = f"""
        SELECT i.id_item, c.destino
        FROM menu_items i
        JOIN menu_categorias c ON i.id_categoria = c.id_categoria
        WHERE i.id_item IN ({placeholders})
        """
        rows = db_manager.fetchall(query, tuple(item_ids))
        return {row['id_item']: row['destino'] for row in rows}

menu_repo = MenuRepository()
