import sqlite3
from flask import g, current_app

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db

def close_db(_error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    get_db().executescript('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE, location TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE
    );
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE COLLATE NOCASE, name TEXT NOT NULL,
        room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
        category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
        quantity INTEGER NOT NULL CHECK(quantity>0), condition TEXT NOT NULL CHECK(condition IN ('Baik','Perlu perbaikan','Rusak')),
        archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1))
    );
    CREATE TABLE IF NOT EXISTS movements (
        id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE RESTRICT,
        from_room INTEGER NOT NULL REFERENCES rooms(id), to_room INTEGER NOT NULL REFERENCES rooms(id),
        quantity INTEGER NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        CHECK(from_room<>to_room)
    );
    CREATE TABLE IF NOT EXISTS inspections (
        id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES items(id), condition TEXT NOT NULL,
        note TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );
    ''')
