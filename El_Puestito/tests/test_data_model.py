import pytest
from unittest.mock import patch
from src.data_model import DataManager

import warnings

@pytest.fixture
def db_temporal():
    # Silenciamos las advertencias de "unclosed database" de la memoria temporal
    warnings.simplefilter("ignore", ResourceWarning)
    
    with patch.object(DataManager, 'run_migration_if_needed'):
        db = DataManager(":memory:")
        return db

def test_agregar_empleado_exitoso(db_temporal):
    db_temporal.add_employee("E001", "Ana Lopez", "Cajera", 101)
    
    empleado = db_temporal.get_employee_by_id("E001")
    
    assert empleado is not None
    assert empleado["nombre"] == "Ana Lopez"
    assert empleado["rol"] == "Cajera"
    assert empleado["fingerprint_id"] == 101

def test_agregar_empleado_id_duplicado(db_temporal):
    db_temporal.add_employee("E001", "Ana Lopez", "Cajera", 101)
    db_temporal.add_employee("E001", "Carlos Perez", "Mesero", 102)
    
    empleados = db_temporal.get_employees()
    
    assert len(empleados) == 1
    assert empleados[0]["nombre"] == "Ana Lopez"

def test_split_order_exitoso(db_temporal):
    db_temporal.execute("INSERT INTO menu_categorias (nombre, destino) VALUES ('Comidas', 'cocina')")
    db_temporal.execute("INSERT INTO menu_items (id_item, id_categoria, nombre, precio, disponible) VALUES ('ITEM1', 1, 'Taco', 50, 1)")
    
    orden = {
        "numero_mesa": "5",
        "order_id": "cliente-xyz",
        "items": [
            {"item_id": "ITEM1", "cantidad": 2, "precio_unitario": 50, "nombre": "Taco"}
        ]
    }
    
    id_orden = db_temporal.create_new_order(orden)
    
    detalle = db_temporal.fetchone("SELECT id_detalle FROM orden_detalle WHERE id_orden = ?", (id_orden,))
    
    items_to_split = [{"id_detalle": detalle['id_detalle'], "cantidad": 1}]
    
    nuevo_id = db_temporal.split_order("5", items_to_split)
    
    detalles_origen = db_temporal.fetchone("SELECT cantidad FROM orden_detalle WHERE id_orden = ?", (id_orden,))
    detalles_nuevo = db_temporal.fetchone("SELECT cantidad FROM orden_detalle WHERE id_orden = ?", (nuevo_id,))
    
    assert nuevo_id is not False
    assert detalles_origen['cantidad'] == 1
    assert detalles_nuevo['cantidad'] == 1