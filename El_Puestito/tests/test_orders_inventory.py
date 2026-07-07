import pytest
from src.database.connection import db_manager
from src.database.repositories.orders import order_repo
from src.database.repositories.inventory import inventory_repo

@pytest.fixture
def setup_menu_and_inventory(clean_db):
    # Insertar categoria
    db_manager.execute("INSERT INTO menu_categorias (id_categoria, nombre, destino) VALUES (1, 'TestCategoria', 'cocina')")
    
    # Insertar un item sin inventario
    db_manager.execute(
        "INSERT INTO menu_items (id_item, id_categoria, nombre, precio, disponible) VALUES (?, ?, ?, ?, ?)",
        ("ITEM_1", 1, "Item Basico", 5000, 1)
    )
    
    # Insertar un item con inventario automatico
    db_manager.execute(
        "INSERT INTO menu_items (id_item, id_categoria, nombre, precio, disponible) VALUES (?, ?, ?, ?, ?)",
        ("ITEM_2_INV", 1, "Item Con Inventario", 6000, 1)
    )
    db_manager.execute(
        "INSERT INTO inventario (nombre, cantidad, es_automatico, id_menu_vinculado) VALUES (?, ?, ?, ?)",
        ("Inventario Item 2", 5, 1, "ITEM_2_INV")
    )
    
    yield

def test_create_order_success(client, api_key, setup_menu_and_inventory):
    """Prueba que una orden valida se inserta correctamente en SQLite"""
    payload = {
        "numero_mesa": "Mesa 1",
        "order_id": "UUID-123",
        "items": [
            {"item_id": "ITEM_1", "cantidad": 2, "notas": "Sin sal"}
        ]
    }
    response = client.post('/nueva-orden', json=payload, headers={"X-API-KEY": api_key})
    assert response.status_code == 200
    
    # Verificar en la base de datos
    orden = db_manager.fetchone("SELECT * FROM ordenes WHERE mesa_key = 'Mesa 1' AND estado = 'activa'")
    assert orden is not None
    
    detalles = db_manager.fetchall("SELECT * FROM orden_detalle WHERE id_orden = ?", (orden['id_orden'],))
    assert len(detalles) == 1
    assert detalles[0]['cantidad'] == 2

def test_create_order_insufficient_stock(client, api_key, setup_menu_and_inventory):
    """Prueba que una orden se rechaza si pide mas inventario del disponible (y verifica rollback)"""
    payload = {
        "numero_mesa": "Mesa 2",
        "order_id": "UUID-456",
        "items": [
            {"item_id": "ITEM_2_INV", "cantidad": 10, "notas": ""}
        ]
    }
    response = client.post('/nueva-orden', json=payload, headers={"X-API-KEY": api_key})
    assert response.status_code == 400
    assert b"Stock insuficiente" in response.data or b"No hay suficiente stock" in response.data
    
    # Verificar rollback: no debe haber orden
    orden = db_manager.fetchone("SELECT * FROM ordenes WHERE mesa_key = 'Mesa 2' AND estado = 'activa'")
    assert orden is None

def test_create_order_invalid_quantity(client, api_key, setup_menu_and_inventory):
    """Prueba que se rechazan ordenes con cantidades nulas o negativas"""
    payload = {
        "numero_mesa": "Mesa 3",
        "order_id": "UUID-789",
        "items": [
            {"item_id": "ITEM_1", "cantidad": -1, "notas": ""}
        ]
    }
    response = client.post('/nueva-orden', json=payload, headers={"X-API-KEY": api_key})
    assert response.status_code == 400
    assert b"Cantidad invalida" in response.data or b"inv\xc3\xa1lida" in response.data

def test_split_order_validation(setup_menu_and_inventory):
    """Prueba la validacion de cuentas divididas en la logica del servicio"""
    # Crear orden base
    db_manager.execute("INSERT INTO ordenes (id_orden, mesa_key, fecha_apertura) VALUES (1, 'Mesa Origen', '2026-01-01')")
    db_manager.execute("INSERT INTO orden_detalle (id_detalle, id_orden, id_item_menu, cantidad, precio_unitario_congelado, nombre_congelado, destino) VALUES (1, 1, 'ITEM_1', 3, 5000, 'Item 1', 'cocina')")
    
    from src.services.order_service import order_service
    # Intentar separar 4 items (solo hay 3)
    exito = order_service.split_order(1, 'Mesa Destino', [{'id_detalle': 1, 'cantidad': 4}])
    assert not exito

def test_remove_item_validation(setup_menu_and_inventory):
    """Prueba que remover articulos devuelve inventario y valida cantidades"""
    db_manager.execute("INSERT INTO ordenes (id_orden, mesa_key, fecha_apertura) VALUES (2, 'Mesa Remove', '2026-01-01')")
    db_manager.execute("INSERT INTO orden_detalle (id_detalle, id_orden, id_item_menu, cantidad, precio_unitario_congelado, nombre_congelado, destino) VALUES (2, 2, 'ITEM_2_INV', 2, 6000, 'Item 2', 'cocina')")
    
    from src.services.order_service import order_service
    # Remover 1 cantidad
    exito = order_service.remove_items_from_order('Mesa Remove', [{'id_detalle': 2, 'cantidad': 1, 'id_item_menu': 'ITEM_2_INV'}])
    assert exito
    
    # Verificar stock restaurado (tenia 5, se inserto a la mala sin restar, asi que si sumamos 1, debe haber 6)
    inv = db_manager.fetchone("SELECT cantidad FROM inventario WHERE id_menu_vinculado = 'ITEM_2_INV'")
    assert inv['cantidad'] == 6
