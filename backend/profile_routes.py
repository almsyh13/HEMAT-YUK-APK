"""
profile_routes.py
-----------------
Endpoint untuk fitur halaman Profile:

  GET    /api/profile/              -> Lihat data profil lengkap
  PUT    /api/profile/              -> Edit nama lengkap (full_name)
  PUT    /api/profile/password      -> Ganti password
  POST   /api/profile/photo         -> Upload foto profil
  DELETE /api/profile/photo         -> Hapus foto profil
  GET    /api/profile/photo/<filename> -> Ambil/tampilkan file foto (untuk <img src="...">)

Konsep BARU yang dipelajari di file ini:
  - Multipart/form-data : format pengiriman file dari frontend ke backend
  - request.files       : cara Flask membaca file yang diunggah
  - werkzeug FileStorage: objek yang merepresentasikan file yang diunggah
  - os.path             : operasi path file di sistem operasi
  - send_from_directory : cara Flask mengirim file (gambar) ke browser/frontend
"""

import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db_connection, BASE_DIR

profile_bp = Blueprint('profile', __name__)

# ============================================================
# KONFIGURASI UPLOAD FOTO
# ============================================================
UPLOAD_FOLDER   = os.path.join(BASE_DIR, 'uploads', 'photos')
ALLOWED_EXT     = {'jpg', 'jpeg', 'png', 'webp'}   # Ekstensi file yang diizinkan
MAX_SIZE_BYTES  = 2 * 1024 * 1024                   # Maks 2 MB

# Buat folder uploads/photos jika belum ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ================================================================
# HELPER FUNCTIONS
# ================================================================
def allowed_file(filename: str) -> bool:
    """
    Cek apakah ekstensi file termasuk yang diizinkan.

    'foto.jpg'  -> split('.') -> ['foto', 'jpg'] -> [-1] -> 'jpg' -> True
    'virus.exe' -> split('.') -> ['virus', 'exe'] -> [-1] -> 'exe' -> False
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def build_photo_url(filename: str | None, request_obj) -> str | None:
    """
    Membangun URL lengkap foto profil.

    Daripada menyimpan URL lengkap di database (yang bisa berubah jika port/domain berubah),
    kita hanya simpan NAMA FILE, lalu URL dibuat secara dinamis saat diperlukan.

    Contoh: 'abc123.jpg' -> 'http://localhost:5000/api/profile/photo/abc123.jpg'
    """
    if not filename:
        return None
    base = request_obj.host_url.rstrip('/')
    return f"{base}/api/profile/photo/{filename}"


def get_user_or_404(user_id):
    """Ambil data user dari DB. Return (conn, user) atau raise 404 response."""
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, username, email, full_name, photo_filename, created_at '
        'FROM users WHERE id = ?',
        (user_id,)
    )
    user = cursor.fetchone()
    if user is None:
        conn.close()
        return None, None
    return conn, user


# ================================================================
# ENDPOINT 1: LIHAT PROFIL
# GET /api/profile/
# ================================================================
@profile_bp.route('/', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Mengembalikan data profil lengkap user yang sedang login.

    Response:
    {
        "success": true,
        "user": {
            "id": 1,
            "username": "hamka",
            "email": "hamka@gmail.com",
            "full_name": "Hamka Syahrul",        <- bisa null jika belum diisi
            "photo_url": "http://localhost:5000/api/profile/photo/abc.jpg",  <- bisa null
            "created_at": "2026-11-19 20:00:00"
        }
    }
    """
    current_user_id = get_jwt_identity()
    conn, user = get_user_or_404(current_user_id)
    if user is None:
        return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404

    conn.close()
    return jsonify({
        'success': True,
        'user': {
            'id':         user['id'],
            'username':   user['username'],
            'email':      user['email'],
            'full_name':  user['full_name'],
            'photo_url':  build_photo_url(user['photo_filename'], request),
            'created_at': user['created_at'],
        }
    }), 200


# ================================================================
# ENDPOINT 2: EDIT PROFIL (full_name dan/atau username)
# PUT /api/profile/
# ================================================================
@profile_bp.route('/', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Mengubah nama lengkap (full_name) dan/atau username user.

    Frontend mengirim JSON (kirim salah satu atau keduanya):
    {
        "full_name": "Hamka Syahrul Chandra",
        "username":  "hamka_baru"
    }

    Aturan username:
    - Minimal 3 karakter, maksimal 30 karakter
    - Hanya boleh huruf, angka, dan underscore (_)
    - Harus UNIK — tidak boleh sama dengan user lain

    Proses:
    1. Ambil full_name dan/atau username dari body
    2. Validasi masing-masing field jika dikirim
    3. Cek keunikan username baru (jika diubah)
    4. Bangun query UPDATE secara dinamis
    5. Return data profil terbaru
    """
    import re  # re = modul Regular Expression untuk validasi format teks

    current_user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Request body kosong'}), 400

    full_name    = data.get('full_name', '').strip()
    new_username = data.get('username',  '').strip()

    # Pastikan minimal satu field dikirim
    if not full_name and not new_username:
        return jsonify({
            'success': False,
            'message': 'Kirim minimal satu field: "full_name" atau "username"'
        }), 400

    # ---- Validasi full_name (jika dikirim) ----
    if full_name and len(full_name) > 100:
        return jsonify({'success': False, 'message': 'Nama lengkap maksimal 100 karakter'}), 400

    # ---- Validasi username (jika dikirim) ----
    if new_username:
        if len(new_username) < 3:
            return jsonify({'success': False, 'message': 'Username minimal 3 karakter'}), 400
        if len(new_username) > 30:
            return jsonify({'success': False, 'message': 'Username maksimal 30 karakter'}), 400

        # Cek format: hanya huruf, angka, underscore
        # re.match() mencocokkan pola dari awal string
        # ^[a-zA-Z0-9_]+$ = hanya karakter a-z, A-Z, 0-9, _
        if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
            return jsonify({
                'success': False,
                'message': 'Username hanya boleh mengandung huruf, angka, dan underscore (_)'
            }), 400

        # Cek apakah username sudah dipakai user LAIN
        # (boleh sama dengan username sendiri — tidak ada perubahan)
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM users WHERE username = ? AND id != ?',
            (new_username, current_user_id)
            # AND id != ? = kecualikan diri sendiri dari pengecekan
        )
        existing = cursor.fetchone()
        conn.close()

        if existing:
            return jsonify({
                'success': False,
                'message': f'Username "{new_username}" sudah digunakan oleh akun lain'
            }), 409  # 409 = Conflict

    # ---- Bangun query UPDATE secara dinamis ----
    # Hanya update kolom yang dikirim, mirip seperti filter transaksi minggu lalu
    updates = []   # list kolom yang akan diupdate: ['full_name = ?', 'username = ?']
    params  = []   # list nilai yang sesuai

    if full_name:
        updates.append('full_name = ?')
        params.append(full_name)

    if new_username:
        updates.append('username = ?')
        params.append(new_username)

    params.append(current_user_id)  # Untuk klausa WHERE id = ?

    conn   = get_db_connection()
    cursor = conn.cursor()

    # Contoh query yang dibangun:
    # "UPDATE users SET full_name = ?, username = ? WHERE id = ?"
    query = f'UPDATE users SET {", ".join(updates)} WHERE id = ?'
    cursor.execute(query, params)
    conn.commit()

    # Ambil data terbaru
    cursor.execute(
        'SELECT id, username, email, full_name, photo_filename, created_at '
        'FROM users WHERE id = ?',
        (current_user_id,)
    )
    user = cursor.fetchone()
    conn.close()

    # Buat pesan sukses yang informatif
    changed = []
    if full_name:    changed.append('nama lengkap')
    if new_username: changed.append('username')
    message = f'{" dan ".join(changed).capitalize()} berhasil diperbarui!'

    return jsonify({
        'success': True,
        'message': message,
        'user': {
            'id':        user['id'],
            'username':  user['username'],
            'email':     user['email'],
            'full_name': user['full_name'],
            'photo_url': build_photo_url(user['photo_filename'], request),
        }
    }), 200


# ================================================================
# ENDPOINT 3: GANTI PASSWORD
# PUT /api/profile/password
# ================================================================
@profile_bp.route('/password', methods=['PUT'])
@jwt_required()
def change_password():
    """
    Mengganti password user.

    Frontend mengirim JSON:
    {
        "current_password": "rahasia123",
        "new_password":     "passwordBaru456",
        "confirm_password": "passwordBaru456"
    }

    Alur keamanan:
    1. Minta password lama untuk verifikasi (user harus tahu password saat ini)
    2. Konfirmasi password baru harus cocok
    3. Validasi panjang password baru
    4. Hash password baru sebelum disimpan
    """
    current_user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Request body kosong'}), 400

    current_password = data.get('current_password', '').strip()
    new_password     = data.get('new_password',     '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    # Validasi semua field wajib ada
    if not current_password or not new_password or not confirm_password:
        return jsonify({
            'success': False,
            'message': 'current_password, new_password, dan confirm_password wajib diisi'
        }), 400

    # Validasi konfirmasi password baru
    if new_password != confirm_password:
        return jsonify({
            'success': False,
            'message': 'Konfirmasi password baru tidak cocok'
        }), 400

    # Validasi panjang password baru
    if len(new_password) < 6:
        return jsonify({
            'success': False,
            'message': 'Password baru minimal 6 karakter'
        }), 400

    # Ambil password lama dari database untuk verifikasi
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE id = ?', (current_user_id,))
    user = cursor.fetchone()

    if user is None:
        conn.close()
        return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404

    # Verifikasi password lama dengan hash di database
    if not check_password_hash(user['password'], current_password):
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Password saat ini salah'
        }), 401

    # Hash password baru & simpan
    hashed_new = generate_password_hash(new_password)
    cursor.execute(
        'UPDATE users SET password = ? WHERE id = ?',
        (hashed_new, current_user_id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Password berhasil diperbarui! Silakan login ulang jika diperlukan.'
    }), 200


# ================================================================
# ENDPOINT 4: UPLOAD FOTO PROFIL
# POST /api/profile/photo
# ================================================================
@profile_bp.route('/photo', methods=['POST'])
@jwt_required()
def upload_photo():
    """
    Mengunggah (upload) foto profil.

    Konsep PENTING - Multipart Form Data:
      Berbeda dengan JSON, file dikirim dalam format "multipart/form-data".
      Frontend menggunakan <input type="file"> atau FormData di JavaScript.
      Flask membaca file dari `request.files`, bukan `request.get_json()`.

    Frontend mengirim FormData dengan field bernama 'photo':
      const formData = new FormData();
      formData.append('photo', fileObject);
      fetch('/api/profile/photo', { method: 'POST', body: formData, headers: { Authorization: ... } })

    Proses:
    1. Cek apakah ada file di request
    2. Validasi nama file & ekstensi
    3. Validasi ukuran file (maks 2 MB)
    4. Generate nama file unik (UUID) agar tidak bertabrakan
    5. Simpan file ke folder uploads/photos/
    6. Hapus foto lama jika ada
    7. Update kolom photo_filename di database
    """
    current_user_id = get_jwt_identity()

    # Langkah 1: Cek apakah file dikirim
    # 'photo' adalah nama field di FormData frontend
    if 'photo' not in request.files:
        return jsonify({
            'success': False,
            'message': 'Tidak ada file yang dikirim. Gunakan field name "photo"'
        }), 400

    file = request.files['photo']  # Objek FileStorage dari werkzeug

    # FileStorage dengan filename kosong artinya user tidak memilih file
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Tidak ada file yang dipilih'}), 400

    # Langkah 2: Validasi ekstensi file
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'message': f'Format file tidak didukung. Gunakan: {", ".join(ALLOWED_EXT)}'
        }), 400

    # Langkah 3: Validasi ukuran file
    # file.seek(0, 2) = pindah ke akhir file; file.tell() = posisi sekarang = ukuran
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)  # Kembali ke awal agar bisa dibaca/disimpan
    if file_size > MAX_SIZE_BYTES:
        return jsonify({
            'success': False,
            'message': f'Ukuran file terlalu besar. Maksimal 2 MB (saat ini: {file_size/1024/1024:.1f} MB)'
        }), 400

    # Langkah 4: Generate nama file unik dengan UUID
    # secure_filename() membersihkan nama file dari karakter berbahaya
    # uuid.uuid4() menghasilkan ID unik seperti: "a3f8c1d2-..."
    ext          = file.filename.rsplit('.', 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{ext}"   # contoh: "a3f8c1d2abc.jpg"

    # Langkah 5: Simpan file ke disk
    save_path = os.path.join(UPLOAD_FOLDER, new_filename)
    file.save(save_path)

    # Langkah 6: Hapus foto lama jika ada (agar tidak penuh)
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT photo_filename FROM users WHERE id = ?', (current_user_id,))
    row = cursor.fetchone()

    if row and row['photo_filename']:
        old_path = os.path.join(UPLOAD_FOLDER, row['photo_filename'])
        if os.path.exists(old_path):
            os.remove(old_path)   # Hapus file lama dari disk

    # Langkah 7: Update database
    cursor.execute(
        'UPDATE users SET photo_filename = ? WHERE id = ?',
        (new_filename, current_user_id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        'success':   True,
        'message':   'Foto profil berhasil diupload!',
        'photo_url': build_photo_url(new_filename, request)
    }), 200


# ================================================================
# ENDPOINT 5: HAPUS FOTO PROFIL
# DELETE /api/profile/photo
# ================================================================
@profile_bp.route('/photo', methods=['DELETE'])
@jwt_required()
def delete_photo():
    """
    Menghapus foto profil user (kembali ke foto default/null).

    Proses:
    1. Ambil nama file foto dari database
    2. Hapus file dari disk
    3. Set photo_filename = NULL di database
    """
    current_user_id = get_jwt_identity()

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT photo_filename FROM users WHERE id = ?', (current_user_id,))
    row = cursor.fetchone()

    if not row or not row['photo_filename']:
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Tidak ada foto profil untuk dihapus'
        }), 404

    # Hapus file dari disk
    file_path = os.path.join(UPLOAD_FOLDER, row['photo_filename'])
    if os.path.exists(file_path):
        os.remove(file_path)

    # Set photo_filename = NULL di database
    cursor.execute(
        'UPDATE users SET photo_filename = NULL WHERE id = ?',
        (current_user_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Foto profil berhasil dihapus'
    }), 200


# ================================================================
# ENDPOINT 6: SERVE / TAMPILKAN FILE FOTO
# GET /api/profile/photo/<filename>
# ================================================================
@profile_bp.route('/photo/<filename>', methods=['GET'])
def serve_photo(filename):
    """
    Endpoint untuk menampilkan / mengunduh file foto profil.

    Ini endpoint PUBLIC (tidak butuh token) agar tag <img> di browser
    bisa langsung memuatnya tanpa perlu header Authorization.

    Contoh pemakaian di HTML frontend:
      <img src="http://localhost:5000/api/profile/photo/abc123.jpg" />

    secure_filename() dipanggil lagi di sini untuk mencegah
    "path traversal attack" (misal: filename = "../../app.py").

    send_from_directory() = fungsi Flask untuk mengirim file secara aman
    """
    safe_name = secure_filename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe_name)
