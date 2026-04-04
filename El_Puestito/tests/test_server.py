import pytest
from unittest.mock import patch
from src.data_model import DataManager
from server.server_worker import ServerWorker

@pytest.fixture
def mock_worker():
    with patch.object(DataManager, 'run_migration_if_needed'):
        db = DataManager(":memory:")
        worker = ServerWorker(db)
        worker.API_KEY = "clave_secreta_test"
        return worker

@pytest.fixture
def client(mock_worker):
    mock_worker.app.config['TESTING'] = True
    with mock_worker.app.test_client() as client:
        yield client

def test_api_rechaza_peticion_sin_auth(client):
    response = client.post('/api/biometric/start-enroll')
    assert response.status_code == 401

def test_api_acepta_peticion_con_auth(client):
    headers = {'X-API-KEY': 'clave_secreta_test'}
    response = client.post('/api/biometric/start-enroll', headers=headers)
    assert response.status_code == 200
    assert response.json['status'] == 'waiting_for_finger'

def test_kds_orders_endpoint_vacio(client):
    response = client.get('/api/kds-orders/cocina')
    assert response.status_code == 200
    assert response.json == []

def test_kds_orders_endpoint_invalido(client):
    response = client.get('/api/kds-orders/bodega')
    assert response.status_code == 400