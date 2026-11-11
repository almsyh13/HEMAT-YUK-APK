"""
auth_routes.py
--------------
File ini berisi semua ENDPOINT (URL) yang berhubungan dengan autentikasi:
- POST /api/auth/register  -> Mendaftar akun baru
- POST /api/auth/login     -> Login dan mendapatkan token
- GET  /api/auth/me        -> Mengecek siapa user yang sedang login (butuh token)

Konsep PENTING:
    Endpoint = URL yang bisa dipanggil oleh frontend
    HTTP Method:
        - POST  : Mengirim data (login, register, buat transaksi)
        - GET   : Mengambil data (lihat profil, lihat riwayat)
        - PUT   : Mengubah data
        - DELETE: Menghapus data
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
import sqlite3

# Blueprint = cara Flask mengelompokkan endpoint yang berkaitan
# Bayangkan seperti "folder" untuk endpoint-endpoint autentikasi
auth_bp = Blueprint('auth', __name__)


# ================================================================
# ENDPOINT 1: REGISTER (Daftar Akun Baru)
# ================================================================
@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Endpoint untuk mendaftar akun baru.
    
    Frontend mengirim JSON seperti ini:
    {
        "username": "hamka",
        "email": "hamka@gmail.com",
        "password": "rahasia123"
    }
    
    Proses:
    1. Ambil data dari request body (JSON yang dikirim frontend)
    2. Validasi: pastikan semua field terisi
    3. Hash password (enkripsi satu arah)
    4. Simpan ke database
    5. Kembalikan response sukses atau error
    """
    
    # Langkah 1: Ambil data JSON dari body request
    data = request.get_json()
    
    # Langkah 2: Validasi input
    # Cek apakah semua field yang dibutuhkan ada dan tidak kosong
    if not data:
        return jsonify({
            'success': False,
            'message': 'Request body tidak boleh kosong'
        }), 400  # 400 = Bad Request

    username = data.get('username', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '').strip()

    # Validasi field kosong
    if not username or not email or not password:
        return jsonify({
            'success': False,
            'message': 'Username, email, dan password wajib diisi'
        }), 400

    # Validasi panjang password
    if len(password) < 6:
        return jsonify({
            'success': False,
            'message': 'Password minimal 6 karakter'
        }), 400

    # Langkah 3: Hash password
    # generate_password_hash() mengubah "rahasia123" menjadi hash seperti:
    # "pbkdf2:sha256:260000$abc123...xyz" — tidak bisa dikembalikan ke aslinya
    hashed_password = generate_password_hash(password)

    # Langkah 4: Simpan ke database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, hashed_password)
            # Tanda ? adalah PLACEHOLDER untuk mencegah SQL Injection!
            # JANGAN pernah tulis: f"INSERT INTO users ... VALUES ('{username}', ...)"
        )
        
        conn.commit()    # Simpan perubahan
        conn.close()     # Tutup koneksi
        
        # Langkah 5: Kembalikan response sukses
        return jsonify({
            'success': True,
            'message': f'Akun "{username}" berhasil dibuat! Silakan login.'
        }), 201  # 201 = Created (berhasil membuat resource baru)

    except sqlite3.IntegrityError:
        # IntegrityError terjadi jika username atau email sudah terdaftar
        # (karena kita set UNIQUE di database)
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Username atau email sudah terdaftar'
        }), 409  # 409 = Conflict


# ================================================================
# ENDPOINT 2: LOGIN
# ================================================================
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Endpoint untuk login.
    
    Frontend mengirim JSON:
    {
        "username": "hamka",
        "password": "rahasia123"
    }
    
    Jika berhasil, backend mengembalikan TOKEN:
    {
        "success": true,
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user": { "id": 1, "username": "hamka", "email": "hamka@gmail.com" }
    }
    
    Token ini disimpan frontend dan dikirim di setiap request berikutnya
    sebagai "bukti" bahwa user sudah login.
    """
    
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'message': 'Request body tidak boleh kosong'
        }), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({
            'success': False,
            'message': 'Username dan password wajib diisi'
        }), 400

    # Cari user di database berdasarkan username
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()  # Ambil satu baris hasil query
    conn.close()

    # Cek apakah user ditemukan DAN password cocok
    # check_password_hash() membandingkan password asli dengan hash di database
    if user is None or not check_password_hash(user['password'], password):
        # PENTING: Jangan bilang "username tidak ditemukan" atau "password salah"
        # Selalu pakai pesan yang sama untuk mencegah enumeration attack!
        return jsonify({
            'success': False,
            'message': 'Username atau password salah'
        }), 401  # 401 = Unauthorized

    # Buat JWT Token
    # identity = identitas user yang disimpan di dalam token
    # Token ini TIDAK disimpan di database, cukup di frontend
    access_token = create_access_token(identity=str(user['id']))

    return jsonify({
        'success': True,
        'message': 'Login berhasil!',
        'token': access_token,
        'user': {
            'id':       user['id'],
            'username': user['username'],
            'email':    user['email']
        }
    }), 200  # 200 = OK


# ================================================================
# ENDPOINT 3: GET CURRENT USER (Cek siapa yang sedang login)
# ================================================================
@auth_bp.route('/me', methods=['GET'])
@jwt_required()  # <-- Decorator ini memastikan request memiliki token yang valid!
def get_current_user():
    """
    Endpoint untuk mengambil data user yang sedang login.
    
    Frontend mengirim request dengan header:
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    
    @jwt_required() otomatis menolak request tanpa token yang valid.
    get_jwt_identity() mengambil user ID yang tersimpan di dalam token.
    """
    
    # Ambil user_id dari token JWT
    current_user_id = get_jwt_identity()
    
    # Cari data user di database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, username, email, created_at FROM users WHERE id = ?',
        (current_user_id,)
        # PERHATIKAN: kita TIDAK SELECT password untuk keamanan!
    )
    user = cursor.fetchone()
    conn.close()

    if user is None:
        return jsonify({
            'success': False,
            'message': 'User tidak ditemukan'
        }), 404  # 404 = Not Found

    return jsonify({
        'success': True,
        'user': {
            'id':         user['id'],
            'username':   user['username'],
            'email':      user['email'],
            'created_at': user['created_at']
        }
    }), 200
