from src.database.connection import db_manager
from logger_setup import setup_logger

logger = setup_logger()

class InventoryRepository:
    def get_inventario_completo(self):
        query = """
        SELECT i.id_inventario, i.nombre, i.cantidad, i.es_automatico, i.id_menu_vinculado, m.nombre as nombre_menu
        FROM inventario i
        LEFT JOIN menu_items m ON i.id_menu_vinculado = m.id_item
        ORDER BY i.nombre;
        """
        return db_manager.fetchall(query)

    def agregar_item_inventario(self, nombre, cantidad, es_automatico=0, id_menu_vinculado=None):
        return db_manager.execute(
            "INSERT INTO inventario (nombre, cantidad, es_automatico, id_menu_vinculado) VALUES (?, ?, ?, ?);",
            (nombre, cantidad, es_automatico, id_menu_vinculado)
        )

    def actualizar_cantidad_inventario(self, id_inventario, nueva_cantidad):
        return db_manager.execute(
            "UPDATE inventario SET cantidad = ? WHERE id_inventario = ?;",
            (nueva_cantidad, id_inventario)
        )

    def eliminar_item_inventario(self, id_inventario):
        return db_manager.execute("DELETE FROM inventario WHERE id_inventario = ?;", (id_inventario,))

inventory_repo = InventoryRepository()
