import csv
import io
from flask import Blueprint, request, jsonify, Response
from .db import get_db
from . import service
api = Blueprint('api', __name__)

def payload():
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValueError('Gunakan objek JSON.')
    return data

def query_items():
    args, clauses = [], ['i.archived=?']
    args.append(1 if request.args.get('archived') == '1' else 0)
    q = request.args.get('q', '').strip()[:100]
    if q:
        clauses.append('(instr(lower(i.name),lower(?))>0 OR instr(lower(i.code),lower(?))>0)')
        args.extend([q, q])
    for key in ('room_id', 'category_id', 'condition'):
        value = request.args.get(key)
        if value:
            clauses.append(f'i.{key}=?')
            args.append(value)
    return get_db().execute('''SELECT i.*,r.name room,c.name category FROM items i
        JOIN rooms r ON r.id=i.room_id JOIN categories c ON c.id=i.category_id WHERE '''
        + ' AND '.join(clauses) + ' ORDER BY i.code', args).fetchall()

@api.get('/api/state')
def state():
    db = get_db()
    return jsonify(rooms=[dict(r) for r in db.execute('SELECT * FROM rooms ORDER BY name')],
                   categories=[dict(r) for r in db.execute('SELECT * FROM categories ORDER BY name')],
                   items=[dict(r) for r in query_items()],
                   totals=dict(db.execute('SELECT count(*) records,coalesce(sum(quantity),0) units FROM items WHERE archived=0').fetchone()))

@api.route('/api/<kind>', methods=['POST'])
@api.route('/api/<kind>/<int:id>', methods=['PUT', 'DELETE'])
def master(kind, id=None):
    if kind not in ('rooms', 'categories'):
        raise ValueError('Jenis data tidak valid.')
    if request.method == 'DELETE':
        service.require(kind, id)
        with get_db():
            get_db().execute(f'DELETE FROM {kind} WHERE id=?', (id,))
    else:
        service.master(kind, payload(), id)
    return jsonify(message='Data disimpan.'), 200

@api.post('/api/items')
def create_item():
    service.save_item(payload())
    return jsonify(message='Barang ditambahkan.'), 201

@api.route('/api/items/<int:id>', methods=['PUT', 'DELETE'])
def item(id):
    if request.method == 'DELETE':
        service.require('items', id)
        with get_db():
            get_db().execute('UPDATE items SET archived=1 WHERE id=?', (id,))
    else:
        service.save_item(payload(), id)
    return jsonify(message='Barang disimpan. Penghapusan memindahkan barang ke arsip.')

@api.post('/api/items/<int:id>/<action>')
def action(id, action):
    if action == 'transfer':
        service.transfer(id, payload())
    elif action == 'inspect':
        service.inspect(id, payload())
    elif action == 'restore':
        service.require('items', id)
        with get_db():
            get_db().execute('UPDATE items SET archived=0 WHERE id=?', (id,))
    else:
        raise ValueError('Tindakan tidak tersedia.')
    return jsonify(message='Tindakan berhasil dicatat.')

@api.get('/api/items/<int:id>/history')
def history(id):
    service.require('items', id)
    db = get_db()
    movements = db.execute('''SELECT m.*,a.name origin,b.name destination FROM movements m
        JOIN rooms a ON a.id=m.from_room JOIN rooms b ON b.id=m.to_room WHERE item_id=? ORDER BY m.id DESC''', (id,))
    inspections = db.execute('SELECT * FROM inspections WHERE item_id=? ORDER BY id DESC', (id,))
    return jsonify(movements=[dict(r) for r in movements], inspections=[dict(r) for r in inspections])

@api.get('/export.csv')
def export():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Kode', 'Barang', 'Ruangan', 'Kategori', 'Jumlah', 'Kondisi'])
    for row in query_items():
        writer.writerow([("'" + str(v)) if str(v).startswith(('=', '+', '-', '@')) else v
                         for v in [row['code'], row['name'], row['room'], row['category'], row['quantity'], row['condition']]])
    return Response('\ufeff' + output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=inventaris.csv'})
