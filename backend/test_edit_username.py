import urllib.request, urllib.error, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'http://localhost:5000'

def req(method, url, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(BASE+url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp: return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())

def show(label, s, r, ok=True):
    tag = '[PASS]' if (r.get('success') == ok) else '[FAIL]'
    print(f'\n{tag} {label}')
    print(f'  Status : {s}')
    print(f'  Body   : {json.dumps(r, indent=4, ensure_ascii=True)}')

def divider(t): print(f'\n{"="*55}\n  {t}\n{"="*55}')

# --- Login ---
divider('PERSIAPAN: Login')
s, r = req('POST', '/api/auth/login', {'username':'hamka_test','password':'passwordBaru456'})
if not r.get('success'):
    s, r = req('POST', '/api/auth/login', {'username':'hamka_test','password':'rahasia123'})
if not r.get('success'):
    print('[ERROR] Login gagal!')
    sys.exit(1)
TOKEN = r['token']
print(f'[OK] Login sukses. Username saat ini: {r["user"]["username"]}')

# --- Test edit profil ---
divider('TEST EDIT USERNAME & NAMA')

# 1. Edit hanya full_name
s, r = req('PUT', '/api/profile/', {'full_name': 'Hamka Updated'}, TOKEN)
show('Edit hanya full_name', s, r)

# 2. Edit hanya username
s, r = req('PUT', '/api/profile/', {'username': 'hamka_baru'}, TOKEN)
show('Edit hanya username -> hamka_baru', s, r)

# 3. Edit keduanya sekaligus
s, r = req('PUT', '/api/profile/', {'full_name': 'Hamka Final', 'username': 'hamka_final'}, TOKEN)
show('Edit keduanya sekaligus', s, r)

# --- Test validasi ---
divider('TEST VALIDASI')

# Daftarkan akun lain untuk tes konflik
req('POST', '/api/auth/register', {'username':'user_lain','email':'lain@test.com','password':'test123'})

# 4. Username sudah dipakai orang lain
s, r = req('PUT', '/api/profile/', {'username': 'user_lain'}, TOKEN)
show('Username sudah dipakai (harus GAGAL 409)', s, r, ok=False)

# 5. Format username salah (ada spasi)
s, r = req('PUT', '/api/profile/', {'username': 'hamka baru!'}, TOKEN)
show('Format username salah/ada spasi (harus GAGAL)', s, r, ok=False)

# 6. Username terlalu pendek
s, r = req('PUT', '/api/profile/', {'username': 'ab'}, TOKEN)
show('Username terlalu pendek (harus GAGAL)', s, r, ok=False)

# 7. Tidak ada field sama sekali
s, r = req('PUT', '/api/profile/', {}, TOKEN)
show('Tidak ada field apapun (harus GAGAL)', s, r, ok=False)

# --- Profil final ---
divider('PROFIL FINAL')
s, r = req('GET', '/api/profile/', token=TOKEN)
show('GET /api/profile/ (konfirmasi perubahan)', s, r)

print('\n' + '='*55)
print('  Test selesai!')
print('='*55)
