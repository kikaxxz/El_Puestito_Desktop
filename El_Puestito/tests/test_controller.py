import pytest
from unittest.mock import patch, MagicMock
from src.data_model import DataManager
from src.app_controller import AppController

@pytest.fixture
def mock_controller():
    with patch.object(DataManager, 'run_migration_if_needed'):
        db = DataManager(":memory:")
        controller = AppController(db)
        return controller

def test_agregar_empleado_emite_senal(mock_controller):
    senal_emitida = False
    
    def on_senal():
        nonlocal senal_emitida
        senal_emitida = True
        
    mock_controller.lista_empleados_actualizada.connect(on_senal)
    
    resultado = mock_controller.agregar_empleado("E999", "Tester", "Cajero", None)
    
    assert resultado is not None
    assert senal_emitida is True

def test_procesar_nueva_orden_dispara_flujos(mock_controller):
    mock_controller.notificar_cambios_mesas = MagicMock()
    
    senal_emitida = False
    def on_senal():
        nonlocal senal_emitida
        senal_emitida = True
        
    mock_controller.ordenes_actualizadas.connect(on_senal)
    
    orden_vacia = {
        "numero_mesa": "10",
        "order_id": "uuid-test-123",
        "items": []
    }
    
    mock_controller.procesar_nueva_orden(orden_vacia)
    
    assert senal_emitida is True
    mock_controller.notificar_cambios_mesas.assert_called_once()