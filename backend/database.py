"""
database.py
-----------
File ini bertugas untuk:
1. Membuat koneksi ke database SQLite
2. Membuat tabel-tabel yang dibutuhkan aplikasi
3. Menyediakan fungsi helper untuk mendapatkan koneksi database

Konsep: SQLite menyimpan seluruh database dalam SATU FILE (.db)
sehingga tidak perlu install software database terpisah.
"""

import sqlite3
import os

# Path ke file database SQLite
# os.path.dirname(__file__) = folder tempat file database.py berada
# Jadi database akan disimpan di: backend/finance_app.db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'finance_app.db')


def get_db_connection():
    """
    Membuat dan mengembalikan koneksi ke database SQLite.
    
    row_factory = sqlite3.Row memungkinkan kita mengakses kolom
    berdasarkan nama (seperti dict), bukan hanya indeks angka.
    
    Contoh:
        row['username']  ✅ (dengan row_factory)
        row[0]           ✅ (tanpa row_factory juga bisa)
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Hasil query bisa diakses seperti dictionary
    return conn


def init_db():
    """
    Inisialisasi database: membuat semua tabel jika belum ada.
    Fungsi ini dipanggil saat pertama kali aplikasi dijalankan.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # ============================================================
    # TABEL: users
    # Menyimpan data akun pengguna
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            email       TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    # Penjelasan kolom:
    # - id: nomor unik otomatis (1, 2, 3, dst.)
    # - username: nama pengguna, harus unik
    # - email: email pengguna, harus unik
    # - password: password yang sudah di-HASH (bukan teks biasa!)
    # - created_at: waktu akun dibuat

    # ============================================================
    # TABEL: transactions
    # Menyimpan data transaksi keuangan
    # (akan digunakan di minggu berikutnya)
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            type            TEXT    NOT NULL CHECK(type IN ('income', 'expense')),
            amount          REAL    NOT NULL CHECK(amount > 0),
            category        TEXT    NOT NULL,
            description     TEXT,
            transaction_date TEXT   DEFAULT (date('now', 'localtime')),
            created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    # Penjelasan kolom:
    # - user_id: mengacu ke kolom 'id' di tabel users (Foreign Key)
    # - type: hanya boleh 'income' (pemasukan) atau 'expense' (pengeluaran)
    # - amount: jumlah uang, harus lebih dari 0
    # - category: kategori transaksi (makan, transportasi, gaji, dll.)
    # - description: keterangan tambahan (opsional)

    conn.commit()   # Simpan perubahan ke file database
    conn.close()    # Tutup koneksi
    print("[OK] Database berhasil diinisialisasi!")
    print(f"[DB] Lokasi database: {DATABASE_PATH}")
