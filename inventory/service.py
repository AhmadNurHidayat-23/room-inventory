from .db import get_db
CONDITIONS = ('Baik', 'Perlu perbaikan', 'Rusak')

def text(data, key, limit=100):
    value = data.get(key, '')
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f'{key}: wajib diisi, maksimal {limit} karakter.')
    return value.strip()

def integer(data, key):
    value = data.get(key)
    if isinstance(value, bool) or not str(value).isdigit() or not 0 < int(value) <= 1000000:
        raise ValueError(f'{key}: gunakan bilangan bulat positif, maksimal 1.000.000.')
    return int(value)

def require(table, id):
    if table not in ('items', 'rooms', 'categories'):
        raise ValueError('Jenis data tidak valid.')
    row = get_db().execute(f'SELECT * FROM {table} WHERE id=?', (id,)).fetchone()
    if row is None:
        raise ValueError('Data tidak ditemukan.')
    return row

def master(kind, data, id=None):
    db = get_db()
    name = text(data, 'name', 80)
    if id:
        require(kind, id)
    with db:
        if kind == 'rooms':
            location = data.get('location', '')
            if not isinstance(location, str) or len(location) > 120:
                raise ValueError('Lokasi maksimal 120 karakter.')
            if id:
                db.execute('UPDATE rooms SET name=?,location=? WHERE id=?', (name, location.strip(), id))
            else:
                db.execute('INSERT INTO rooms(name,location) VALUES(?,?)', (name, location.strip()))
        elif kind == 'categories':
            if id:
                db.execute('UPDATE categories SET name=? WHERE id=?', (name, id))
            else:
                db.execute('INSERT INTO categories(name) VALUES(?)', (name,))
        else:
            raise ValueError('Jenis data tidak valid.')

def save_item(data, id=None):
    db = get_db()
    code, name = text(data, 'code', 40).upper(), text(data, 'name')
    category, quantity = integer(data, 'category_id'), integer(data, 'quantity')
    require('categories', category)
    if id:
        old = require('items', id)
        if old['archived']:
            raise ValueError('Pulihkan barang dari arsip sebelum mengubahnya.')
        if 'room_id' in data and integer(data, 'room_id') != old['room_id']:
            raise ValueError('Gunakan formulir perpindahan untuk mengubah ruangan.')
        room = old['room_id']
        condition = old['condition']
        if 'condition' in data and data['condition'] != condition:
            raise ValueError('Gunakan pemeriksaan untuk mengubah kondisi.')
    else:
        room = integer(data, 'room_id')
        require('rooms', room)
        condition = data.get('condition')
        if condition not in CONDITIONS:
            raise ValueError('Kondisi tidak valid.')
    with db:
        if id:
            db.execute('UPDATE items SET code=?,name=?,category_id=?,quantity=? WHERE id=?', (code, name, category, quantity, id))
        else:
            db.execute('INSERT INTO items(code,name,room_id,category_id,quantity,condition) VALUES(?,?,?,?,?,?)',
                       (code, name, room, category, quantity, condition))

def transfer(id, data):
    db = get_db()
    to_room, note = integer(data, 'room_id'), text(data, 'note', 500)
    try:
        db.execute('BEGIN IMMEDIATE')
        item = require('items', id)
        require('rooms', to_room)
        if item['archived'] or item['room_id'] == to_room:
            raise ValueError('Pilih ruangan berbeda untuk barang aktif.')
        db.execute('INSERT INTO movements(item_id,from_room,to_room,quantity,note) VALUES(?,?,?,?,?)',
                   (id, item['room_id'], to_room, item['quantity'], note))
        db.execute('UPDATE items SET room_id=? WHERE id=?', (to_room, id))
        db.commit()
    except Exception:
        db.rollback()
        raise

def inspect(id, data):
    db = get_db()
    condition, note = data.get('condition'), text(data, 'note', 500)
    if condition not in CONDITIONS:
        raise ValueError('Kondisi tidak valid.')
    try:
        db.execute('BEGIN IMMEDIATE')
        if require('items', id)['archived']:
            raise ValueError('Barang dalam arsip.')
        db.execute('INSERT INTO inspections(item_id,condition,note) VALUES(?,?,?)', (id, condition, note))
        db.execute('UPDATE items SET condition=? WHERE id=?', (condition, id))
        db.commit()
    except Exception:
        db.rollback()
        raise
