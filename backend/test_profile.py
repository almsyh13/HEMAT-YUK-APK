"""
test_profile.py
---------------
Script untuk menguji semua endpoint fitur Profile:
  - Lihat profil
  - Edit nama lengkap
  - Ganti password
  - Upload foto profil
  - Hapus foto profil

Jalankan: python test_profile.py
(Pastikan server app.py sudah berjalan!)
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:5000"
TOKEN    = None


# ================================================================
# HELPER FUNCTIONS
# ================================================================
def req(method, endpoint, data=None, token=None, params=None):
    """Kirim JSON request."""
    url = BASE_URL + endpoint
    if params:
        url += '?' + urllib.parse.urlencode(params)
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data).encode('utf-8') if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def req_multipart(endpoint, field_name, file_path, token=None):
    """
    Kirim file (multipart/form-data) ke endpoint.

    Multipart adalah format khusus untuk mengirim file melalui HTTP.
    Browser melakukan ini secara otomatis saat user submit <form enctype="multipart/form-data">.
    Di Python kita harus membangunnya secara manual.
    """
    url      = BASE_URL + endpoint
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'

    with open(file_path, 'rb') as f:
        file_data = f.read()

    filename = os.path.basename(file_path)
    ext      = filename.rsplit('.', 1)[-1].lower()
    mime     = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'png': 'image/png', 'webp': 'image/webp'}.get(ext, 'application/octet-stream')

    # Bangun body multipart secara manual
    body  = f'--{boundary}\r\n'.encode()
    body += f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
    body += f'Content-Type: {mime}\r\n\r\n'.encode()
    body += file_data
    body += f'\r\n--{boundary}--\r\n'.encode()

    headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    r = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def show(label, status, resp, expect_success=True):
    is_success  = resp.get('success', False)
    test_passed = (is_success == expect_success)
    tag = "[PASS]" if test_passed else "[FAIL]"
    print(f"\n{tag} {label}")
    print(f"      Status : {status}")
    print(f"      Body   : {json.dumps(resp, indent=8, ensure_ascii=True)}")


def divider(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ================================================================
# PERSIAPAN: Login
# ================================================================
divider("PERSIAPAN: Login")

req('POST', '/api/auth/register', {
    "username": "hamka_test",
    "email":    "hamka_test@gmail.com",
    "password": "rahasia123"
})

status, resp = req('POST', '/api/auth/login', {
    "username": "hamka_test",
    "password": "rahasia123"
})
show("Login", status, resp)

if not resp.get('success'):
    print("[ERROR] Login gagal!")
    sys.exit(1)

TOKEN = resp['token']
print(f"\n  Token berhasil diperoleh.")


# ================================================================
# TEST 1: LIHAT PROFIL
# ================================================================
divider("TEST 1: LIHAT PROFIL")

status, resp = req('GET', '/api/profile/', token=TOKEN)
show("GET /api/profile/ (profil awal)", status, resp)


# ================================================================
# TEST 2: EDIT NAMA LENGKAP
# ================================================================
divider("TEST 2: EDIT NAMA LENGKAP")

status, resp = req('PUT', '/api/profile/', token=TOKEN,
                   data={"full_name": "Hamka Syahrul Chandra"})
show("PUT /api/profile/ (ganti nama)", status, resp)

# Validasi: nama kosong
status, resp = req('PUT', '/api/profile/', token=TOKEN, data={"full_name": ""})
show("PUT /api/profile/ (nama kosong - harus GAGAL)", status, resp, expect_success=False)

# Lihat profil lagi untuk konfirmasi
status, resp = req('GET', '/api/profile/', token=TOKEN)
show("GET /api/profile/ (setelah edit nama)", status, resp)


# ================================================================
# TEST 3: GANTI PASSWORD
# ================================================================
divider("TEST 3: GANTI PASSWORD")

# Ganti dengan data benar
status, resp = req('PUT', '/api/profile/password', token=TOKEN, data={
    "current_password": "rahasia123",
    "new_password":     "passwordBaru456",
    "confirm_password": "passwordBaru456"
})
show("PUT /api/profile/password (data benar)", status, resp)

# Validasi: password lama salah
status, resp = req('PUT', '/api/profile/password', token=TOKEN, data={
    "current_password": "passwordSalah",
    "new_password":     "apapun123",
    "confirm_password": "apapun123"
})
show("PUT /api/profile/password (password lama salah - harus GAGAL)", status, resp, expect_success=False)

# Validasi: konfirmasi tidak cocok
status, resp = req('PUT', '/api/profile/password', token=TOKEN, data={
    "current_password": "passwordBaru456",
    "new_password":     "abc123",
    "confirm_password": "xyz999"
})
show("PUT /api/profile/password (konfirmasi tidak cocok - harus GAGAL)", status, resp, expect_success=False)

# Validasi: password baru terlalu pendek
status, resp = req('PUT', '/api/profile/password', token=TOKEN, data={
    "current_password": "passwordBaru456",
    "new_password":     "abc",
    "confirm_password": "abc"
})
show("PUT /api/profile/password (terlalu pendek - harus GAGAL)", status, resp, expect_success=False)

# Login dengan password baru untuk verifikasi
status, resp = req('POST', '/api/auth/login', {
    "username": "hamka_test",
    "password": "passwordBaru456"
})
show("Login dengan password BARU (verifikasi perubahan)", status, resp)

# Update token jika login berhasil
if resp.get('success'):
    TOKEN = resp['token']
    print("  Token diperbarui dengan password baru.")


# ================================================================
# TEST 4: UPLOAD FOTO PROFIL
# ================================================================
divider("TEST 4: UPLOAD FOTO PROFIL")

# Buat file dummy PNG 1x1 pixel untuk test
# Ini adalah byte PNG valid terkecil yang bisa dibuat
dummy_png = bytes([
    0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A,  # PNG signature
    0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52,  # IHDR chunk length + type
    0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,  # width=1, height=1
    0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,  # bit depth, color type
    0xDE,0x00,0x00,0x00,0x0C,0x49,0x44,0x41,  # IDAT chunk
    0x54,0x08,0xD7,0x63,0xF8,0xCF,0xC0,0x00,
    0x00,0x00,0x02,0x00,0x01,0xE2,0x21,0xBC,
    0x33,0x00,0x00,0x00,0x00,0x49,0x45,0x4E,  # IEND chunk
    0x44,0xAE,0x42,0x60,0x82
])
test_photo_path = 'test_photo.png'
with open(test_photo_path, 'wb') as f:
    f.write(dummy_png)
print(f"\n  File test dibuat: {test_photo_path} ({len(dummy_png)} bytes)")

# Upload foto
status, resp = req_multipart('/api/profile/photo', 'photo', test_photo_path, token=TOKEN)
show("POST /api/profile/photo (upload foto PNG)", status, resp)

# Lihat profil — photo_url harus sudah terisi
status, resp = req('GET', '/api/profile/', token=TOKEN)
show("GET /api/profile/ (setelah upload foto)", status, resp)
if resp.get('success') and resp['user'].get('photo_url'):
    print(f"\n  URL foto: {resp['user']['photo_url']}")

# Upload dengan field name yang salah (harus GAGAL)
status, resp = req_multipart('/api/profile/photo', 'gambar',  # salah: harusnya 'photo'
                             test_photo_path, token=TOKEN)
show("POST /api/profile/photo (field name salah - harus GAGAL)", status, resp, expect_success=False)


# ================================================================
# TEST 5: HAPUS FOTO PROFIL
# ================================================================
divider("TEST 5: HAPUS FOTO PROFIL")

status, resp = req('DELETE', '/api/profile/photo', token=TOKEN)
show("DELETE /api/profile/photo (hapus foto)", status, resp)

# Hapus lagi — seharusnya 404 karena tidak ada foto
status, resp = req('DELETE', '/api/profile/photo', token=TOKEN)
show("DELETE /api/profile/photo (hapus lagi - harus GAGAL 404)", status, resp, expect_success=False)

# Konfirmasi foto sudah null
status, resp = req('GET', '/api/profile/', token=TOKEN)
show("GET /api/profile/ (setelah hapus foto - photo_url harus null)", status, resp)


# ================================================================
# CLEANUP
# ================================================================
if os.path.exists(test_photo_path):
    os.remove(test_photo_path)
    print(f"\n  File test {test_photo_path} dihapus.")

print("\n" + "="*60)
print("  Semua test profile selesai!")
print("="*60 + "\n")
