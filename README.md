# Room Inventory

Inventaris barang berdasarkan ruangan.

## Fitur utama

- CRUD ruangan, kategori, inventaris; kode unik, jumlah dan kondisi.
- Perpindahan seluruh unit per kode secara atomik dan riwayat pemeriksaan.
- Pencarian, filter, CSV serta arsip inventaris yang dapat dipulihkan.

## Teknologi

Python 3.13, Flask, SQLite, HTML5, CSS3, JavaScript.

## Cara instalasi


~~~powershell
cd C:\laragon\www\room-inventory
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
~~~


## Cara menjalankan


~~~powershell
.\.venv\Scripts\python.exe run.py
~~~

Buka http://127.0.0.1:5321. Jika Python belum masuk PATH, gunakan lokasi python.exe terpasang saat membuat virtual environment. Database dan kunci sesi dibuat otomatis di folder instance dan tidak dilacak Git. Waktu riwayat ditampilkan dalam WIB. Pengujian: .\.venv\Scripts\python.exe -m pytest.
