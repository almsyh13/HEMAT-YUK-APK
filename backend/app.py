"""
app.py
------
File UTAMA aplikasi Flask.
Ini adalah titik masuk (entry point) aplikasi — file yang pertama dijalankan.

Tugas file ini:
1. Membuat instance aplikasi Flask
2. Mengkonfigurasi JWT (sistem token)
3. Mengaktifkan CORS (izin akses dari frontend)
4. Mendaftarkan semua Blueprint (kelompok endpoint)
5. Menjalankan server development
"""

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from datetime import timedelta

# Import fungsi inisialisasi database
from database import init_db

# Import Blueprint autentikasi (dari file auth_routes.py)
from auth_routes import auth_bp


# ============================================================
# 1. BUAT INSTANCE FLASK
# ============================================================
app = Flask(__name__)


# ============================================================
# 2. KONFIGURASI APLIKASI
# ============================================================
app.config['SECRET_KEY'] = 'hsc-finance-secret-key-ganti-ini-di-production'
# SECRET_KEY digunakan untuk menandatangani JWT token agar tidak bisa dipalsukan
# Di production, gunakan string yang panjang dan acak!

app.config['JWT_SECRET_KEY'] = 'hsc-jwt-secret-key-ganti-ini-di-production'
# JWT_SECRET_KEY khusus untuk menandatangani JWT token

app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
# Token akan kedaluwarsa setelah 24 jam — user harus login ulang


# ============================================================
# 3. INISIALISASI EXTENSIONS
# ============================================================
jwt = JWTManager(app)
# JWTManager mengelola pembuatan dan validasi JWT token

CORS(app, resources={r"/api/*": {"origins": "*"}})
# CORS mengizinkan frontend (dari domain/port berbeda) mengakses API kita
# origins="*" artinya izinkan dari mana saja (untuk development)
# Di production, ganti dengan domain frontend yang spesifik


# ============================================================
# 4. DAFTARKAN BLUEPRINT (KELOMPOK ENDPOINT)
# ============================================================
app.register_blueprint(auth_bp, url_prefix='/api/auth')
# Semua endpoint di auth_bp akan diawali dengan /api/auth
# Contoh: route '/login' di auth_bp akan menjadi '/api/auth/login'

# Catatan: Blueprint lain akan ditambahkan di minggu berikutnya
# app.register_blueprint(transaction_bp, url_prefix='/api/transactions')


# ============================================================
# 5. ENDPOINT UTAMA (Health Check)
# ============================================================
@app.route('/')
def home():
    """
    Endpoint untuk mengecek apakah server berjalan dengan baik.
    Biasa disebut 'health check' endpoint.
    """
    return jsonify({
        'success': True,
        'message': 'HSC Finance API berjalan dengan baik! 🚀',
        'version': '1.0.0',
        'endpoints': {
            'POST /api/auth/register': 'Daftar akun baru',
            'POST /api/auth/login':    'Login',
            'GET  /api/auth/me':       'Info user yang sedang login (butuh token)'
        }
    })


# ============================================================
# 6. ERROR HANDLER
# ============================================================
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """Dipanggil ketika token sudah kedaluwarsa."""
    return jsonify({
        'success': False,
        'message': 'Token sudah kedaluwarsa. Silakan login kembali.'
    }), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    """Dipanggil ketika token tidak valid."""
    return jsonify({
        'success': False,
        'message': 'Token tidak valid.'
    }), 401


@jwt.unauthorized_loader
def missing_token_callback(error):
    """Dipanggil ketika request tidak menyertakan token."""
    return jsonify({
        'success': False,
        'message': 'Token diperlukan untuk mengakses endpoint ini.'
    }), 401


# ============================================================
# 7. JALANKAN SERVER
# ============================================================
if __name__ == '__main__':
    # Inisialisasi database saat pertama kali dijalankan
    # Ini akan membuat file finance_app.db dan tabel-tabelnya
    init_db()
    
    print("\n" + "="*50)
    print("  HSC Finance API Server - v1.0.0")
    print("="*50)
    print("  Server berjalan di: http://localhost:5000")
    print("  Health check:       http://localhost:5000/")
    print("  Tekan Ctrl+C untuk menghentikan server")
    print("="*50 + "\n")
    
    app.run(
        host='0.0.0.0',   # Bisa diakses dari IP manapun di jaringan lokal
        port=5000,         # Port yang digunakan
        debug=True         # Mode debug: server auto-restart saat file diubah
                           # JANGAN gunakan debug=True di production!
    )
