import os
import sys
import tempfile
import pytest
import sqlite3

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.join(base_dir, 'src'))

# Establecer la base de datos de pruebas ANTES de importar otros modulos de la app
db_fd, db_path = tempfile.mkstemp(suffix='.db')
os.environ['PUESTITO_DB_PATH'] = db_path
os.environ['TESTING'] = 'true'

from src.database.connection import db_manager
from src.database.schema_manager import SchemaManager
from server.server_worker import ServerWorker
from src.app_controller import AppController

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    # Inicializa el esquema en la base de datos temporal
    schema = SchemaManager()
    schema.initialize_schema()
    yield
    
    # Limpieza: cerrar conexiones y borrar el archivo temporal
    db_manager.close_conn_for_thread()
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def clean_db():
    """Borra todos los datos de las tablas antes de cada test para tener un estado predecible."""
    db_manager.execute("DELETE FROM orden_detalle")
    db_manager.execute("DELETE FROM inventario")
    db_manager.execute("DELETE FROM ordenes")
    db_manager.execute("DELETE FROM menu_items")
    db_manager.execute("DELETE FROM menu_categorias")
    db_manager.execute("DELETE FROM eventos_asistencia")
    db_manager.execute("DELETE FROM empleados")
    yield

@pytest.fixture
def worker():
    # El ServerWorker inicializa la app Flask
    _worker = ServerWorker()
    return _worker

@pytest.fixture
def client(worker):
    worker.app.config['TESTING'] = True
    with worker.app.test_client() as client:
        yield client

@pytest.fixture
def api_key(worker):
    return worker.API_KEY

@pytest.fixture
def app_controller():
    return AppController()
