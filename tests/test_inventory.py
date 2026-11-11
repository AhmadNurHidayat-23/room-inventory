import csv
import io
import sqlite3
import pytest
from inventory import create_app

@pytest.fixture
def env(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'test.sqlite')})
    client = app.test_client()
    client.get('/')
    with client.session_transaction() as session:
        token = session['csrf']
    headers = {'X-CSRF-Token': token}
    def call(path, values=None, method='post'):
        return getattr(client, method)('/api/' + path, json=values, headers=headers)
    call('rooms', {'name': 'Ruang A', 'location': 'Lantai 1'})
    call('rooms', {'name': 'Ruang B', 'location': 'Lantai 2'})
    call('categories', {'name': 'Elektronik'})
    call('items', {'code': 'INV-01', 'name': 'Monitor', 'room_id': 1, 'category_id': 1, 'quantity': 2, 'condition': 'Baik'})
    return app, client, call, tmp_path

def test_crud_and_relations(env):
    _, client, call, _ = env
    assert call('rooms/1', {'name': 'Studio', 'location': 'L1'}, 'put').status_code == 200
    assert call('items/1', {'code': 'INV-01', 'name': 'Monitor besar', 'category_id': 1, 'quantity': 3}, 'put').status_code == 200
    assert call('rooms/1', method='delete').status_code == 409
    assert call('categories/1', method='delete').status_code == 409
    assert client.get('/api/state').json['items'][0]['quantity'] == 3
    assert call('items/1', method='delete').status_code == 200
    assert client.get('/api/state').json['items'] == []
    assert len(client.get('/api/state?archived=1').json['items']) == 1
    assert call('items/1/restore').status_code == 200
    assert len(client.get('/api/state').json['items']) == 1

def test_unique_and_validation(env):
    _, _, call, _ = env
    assert call('items', {'code': 'inv-01', 'name': 'Duplikat', 'room_id': 1, 'category_id': 1, 'quantity': 1, 'condition': 'Baik'}).status_code == 409
    for q in [-1, 0, 1.5, True, '1.2']:
        assert call('items/1', {'code': 'INV-01', 'name': 'Monitor', 'category_id': 1, 'quantity': q}, 'put').status_code == 400
    assert call('rooms', {'name': ' '}).status_code == 400

def test_atomic_transfer_and_history(env):
    _, client, call, _ = env
    assert call('items/1/transfer', {'room_id': 2, 'note': 'Relokasi'}).status_code == 200
    item = client.get('/api/state').json['items'][0]
    history = client.get('/api/items/1/history').json['movements']
    assert item['room_id'] == 2 and history[0]['to_room'] == 2 and history[0]['from_room'] == 1
    assert history[0]['quantity'] == 2
    assert call('items/1/transfer', {'room_id': 999, 'note': 'Gagal'}).status_code == 400
    assert call('items/1/transfer', {'room_id': 2, 'note': 'Sama'}).status_code == 400
    assert len(client.get('/api/items/1/history').json['movements']) == 1
    assert client.get('/api/state').json['items'][0]['room_id'] == 2

def test_transaction_rolls_back_on_insert_failure(env):
    app, client, call, _ = env
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("CREATE TRIGGER refuse_move BEFORE UPDATE OF room_id ON items BEGIN SELECT RAISE(ABORT,'blocked'); END")
    assert call('items/1/transfer', {'room_id': 2, 'note': 'Ditolak trigger'}).status_code == 409
    assert client.get('/api/items/1/history').json['movements'] == []
    assert client.get('/api/state').json['items'][0]['room_id'] == 1

def test_inspection_and_location_guard(env):
    _, client, call, _ = env
    assert call('items/1/inspect', {'condition': 'Rusak', 'note': 'Panel pecah'}).status_code == 200
    assert client.get('/api/state').json['items'][0]['condition'] == 'Rusak'
    assert len(client.get('/api/items/1/history').json['inspections']) == 1
    assert call('items/1', {'code': 'INV-01', 'name': 'Monitor', 'category_id': 1, 'quantity': 2, 'room_id': 2}, 'put').status_code == 400

def test_filter_csv_and_csrf(env):
    _, client, _, _ = env
    assert len(client.get('/api/state?q=monitor&room_id=1&category_id=1&condition=Baik').json['items']) == 1
    assert client.get('/api/state?room_id=2').json['items'] == []
    res = client.get('/export.csv')
    assert res.status_code == 200
    rows = list(csv.reader(io.StringIO(res.data.decode('utf-8-sig'))))
    assert rows[1] == ['INV-01', 'Monitor', 'Ruang A', 'Elektronik', '2', 'Baik']
    assert client.post('/api/rooms', json={'name': 'X'}).status_code == 403

def test_database_persists_and_foreign_keys(env):
    app, _, call, _ = env
    call('items/1/transfer', {'room_id': 2, 'note': 'Pindah'})
    restarted = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']})
    assert restarted.test_client().get('/api/state').json['items'][0]['room_id'] == 2
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'

def test_empty_master_crud(env):
    _, _, call, _ = env
    assert call('rooms', {'name': 'Kosong'}).status_code == 200
    assert call('rooms/3', {'name': 'Kosong 2'}, 'put').status_code == 200
    assert call('rooms/3', method='delete').status_code == 200
    assert call('categories', {'name': 'Cadangan'}).status_code == 200
    assert call('categories/2', {'name': 'Perabot'}, 'put').status_code == 200
    assert call('categories/2', method='delete').status_code == 200
