"""
test_api.py
-----------
Script untuk menguji semua endpoint API autentikasi.
Jalankan: python test_api.py
(Pastikan server app.py sudah berjalan terlebih dahulu!)
"""

import urllib.request
import urllib.parse
import json
import sys

# Fix Windows terminal encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:5000"

def send_request(method, endpoint, data=None, token=None):
    """Helper function untuk mengirim HTTP request."""
    url = BASE_URL + endpoint
    
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    body = json.dumps(data).encode('utf-8') if data else None
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def print_result(test_name, status, response):
    """Menampilkan hasil test dengan rapi."""
    status_emoji = "[PASS]" if str(status).startswith('2') else "[FAIL]"
    print(f"\n{status_emoji} {test_name}")
    print(f"   Status Code : {status}")
    print(f"   Response    : {json.dumps(response, indent=4, ensure_ascii=True)}")


print("\n" + "="*60)
print("  TESTING HSC Finance API - Autentikasi")
print("="*60)

# ============================================================
# TEST 1: Health Check
# ============================================================
print("\n--- TEST 1: Health Check ---")
status, response = send_request('GET', '/')
print_result("GET /", status, response)

# ============================================================
# TEST 2: Register akun baru
# ============================================================
print("\n--- TEST 2: Register ---")
status, response = send_request('POST', '/api/auth/register', {
    "username": "hamka_test",
    "email": "hamka_test@gmail.com",
    "password": "rahasia123"
})
print_result("POST /api/auth/register (data valid)", status, response)

# ============================================================
# TEST 3: Register dengan data duplikat
# ============================================================
print("\n--- TEST 3: Register Duplikat ---")
status, response = send_request('POST', '/api/auth/register', {
    "username": "hamka_test",
    "email": "hamka_test@gmail.com",
    "password": "rahasia123"
})
print_result("POST /api/auth/register (username sama - harus GAGAL)", status, response)

# ============================================================
# TEST 4: Register dengan data tidak lengkap
# ============================================================
print("\n--- TEST 4: Register Data Tidak Lengkap ---")
status, response = send_request('POST', '/api/auth/register', {
    "username": "user_baru"
    # Tidak ada email dan password
})
print_result("POST /api/auth/register (tidak lengkap - harus GAGAL)", status, response)

# ============================================================
# TEST 5: Login berhasil
# ============================================================
print("\n--- TEST 5: Login ---")
status, response = send_request('POST', '/api/auth/login', {
    "username": "hamka_test",
    "password": "rahasia123"
})
print_result("POST /api/auth/login (data benar)", status, response)

# Simpan token untuk test berikutnya
token = response.get('token')

# ============================================================
# TEST 6: Login dengan password salah
# ============================================================
print("\n--- TEST 6: Login Password Salah ---")
status, response = send_request('POST', '/api/auth/login', {
    "username": "hamka_test",
    "password": "passwordsalah"
})
print_result("POST /api/auth/login (password salah - harus GAGAL)", status, response)

# ============================================================
# TEST 7: Akses /me dengan token
# ============================================================
print("\n--- TEST 7: Get Current User (dengan token) ---")
if token:
    status, response = send_request('GET', '/api/auth/me', token=token)
    print_result("GET /api/auth/me (dengan token valid)", status, response)
else:
    print("   [SKIP] Token tidak tersedia (login gagal)")

# ============================================================
# TEST 8: Akses /me tanpa token
# ============================================================
print("\n--- TEST 8: Get Current User (tanpa token) ---")
status, response = send_request('GET', '/api/auth/me')  # Tanpa token
print_result("GET /api/auth/me (tanpa token - harus GAGAL)", status, response)

print("\n" + "="*60)
print("  Testing selesai!")
print("="*60 + "\n")
