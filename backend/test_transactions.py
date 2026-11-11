"""
test_transactions.py
--------------------
Script untuk menguji endpoint transaksi:
  - Dashboard (saldo, pemasukan, pengeluaran)
  - Tambah transaksi baru
  - Riwayat transaksi dengan filter
  - Hapus transaksi

Jalankan dengan: python test_transactions.py
(Pastikan server app.py sudah berjalan!)
"""

import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:5000"
TOKEN    = None   # Akan diisi setelah login


# ================================================================
# HELPER FUNCTIONS
# ================================================================
def req(method, endpoint, data=None, token=None, params=None):
    """Kirim HTTP request dan kembalikan (status_code, response_dict)."""
    url = BASE_URL + endpoint
    if params:
        url += '?' + urllib.parse.urlencode(params)

    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    body = json.dumps(data).encode('utf-8') if data else None
    request_obj = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request_obj) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def show(label, status, resp, expect_success=True):
    """Cetak hasil test dengan rapi."""
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
# PERSIAPAN: Login dulu untuk mendapatkan token
# ================================================================
divider("PERSIAPAN: Login")

# Coba register dulu (mungkin sudah ada, tidak apa-apa)
req('POST', '/api/auth/register', {
    "username": "hamka_test",
    "email":    "hamka_test@gmail.com",
    "password": "rahasia123"
})

status, resp = req('POST', '/api/auth/login', {
    "username": "hamka_test",
    "password": "rahasia123"
})
show("Login sebelum testing", status, resp)

if not resp.get('success'):
    print("\n[ERROR] Login gagal! Pastikan server berjalan dan akun sudah ada.")
    sys.exit(1)

TOKEN = resp['token']
print(f"\n  Token berhasil diperoleh (berlaku 24 jam).")


# ================================================================
# TEST DASHBOARD - Awal (harus semua 0 jika belum ada transaksi)
# ================================================================
divider("TEST DASHBOARD")

status, resp = req('GET', '/api/transactions/dashboard', token=TOKEN)
show("Dashboard (sebelum ada transaksi)", status, resp)


# ================================================================
# TEST KATEGORI
# ================================================================
divider("TEST KATEGORI")

status, resp = req('GET', '/api/transactions/categories', token=TOKEN)
show("Daftar kategori income & expense", status, resp)


# ================================================================
# TEST TAMBAH TRANSAKSI
# ================================================================
divider("TEST TAMBAH TRANSAKSI")

# Tambah beberapa transaksi pemasukan
test_data = [
    # (label, payload, expect_success)
    ("Tambah pemasukan: Gaji 3jt", {
        "type": "income", "amount": 3000000,
        "category": "Gaji", "description": "Gaji Oktober",
        "transaction_date": "2026-11-01"
    }, True),
    ("Tambah pemasukan: Freelance 500rb", {
        "type": "income", "amount": 500000,
        "category": "Freelance", "description": "Desain logo",
        "transaction_date": "2026-11-05"
    }, True),
    ("Tambah pengeluaran: Makan 50rb", {
        "type": "expense", "amount": 50000,
        "category": "Makan", "description": "Makan siang warteg",
        "transaction_date": "2026-11-10"
    }, True),
    ("Tambah pengeluaran: Transportasi 30rb", {
        "type": "expense", "amount": 30000,
        "category": "Transportasi", "description": "Grab ke kampus",
        "transaction_date": "2026-11-11"
    }, True),
    ("Tambah pengeluaran: Belanja 200rb", {
        "type": "expense", "amount": 200000,
        "category": "Belanja", "description": "Beli sepatu",
        "transaction_date": "2026-11-11"
    }, True),
    # --- Test validasi ---
    ("VALIDASI: Nominal negatif (harus GAGAL)", {
        "type": "income", "amount": -100,
        "category": "Gaji", "description": "test",
        "transaction_date": "2026-11-11"
    }, False),
    ("VALIDASI: Kategori salah jenis (harus GAGAL)", {
        "type": "income", "amount": 50000,
        "category": "Makan",   # Makan adalah kategori expense!
        "description": "test", "transaction_date": "2026-11-11"
    }, False),
    ("VALIDASI: Field kosong (harus GAGAL)", {
        "type": "income"
        # Tidak ada amount, category, transaction_date
    }, False),
]

created_ids = []
for label, payload, expect in test_data:
    status, resp = req('POST', '/api/transactions/', data=payload, token=TOKEN)
    show(label, status, resp, expect_success=expect)
    if resp.get('success') and 'transaction' in resp:
        created_ids.append(resp['transaction']['id'])


# ================================================================
# TEST DASHBOARD - Setelah ada transaksi
# ================================================================
divider("TEST DASHBOARD (setelah ada transaksi)")

status, resp = req('GET', '/api/transactions/dashboard', token=TOKEN)
show("Dashboard (setelah transaksi ditambah)", status, resp)

if resp.get('success'):
    d = resp['dashboard']
    print(f"\n      Ringkasan Keuangan:")
    print(f"        Total Pemasukan  : Rp {d['total_income']:,.0f}  ({d['income_count']} transaksi)")
    print(f"        Total Pengeluaran: Rp {d['total_expense']:,.0f}  ({d['expense_count']} transaksi)")
    print(f"        Sisa Saldo       : Rp {d['balance']:,.0f}")


# ================================================================
# TEST RIWAYAT TRANSAKSI (dengan filter)
# ================================================================
divider("TEST RIWAYAT TRANSAKSI")

# Semua transaksi
status, resp = req('GET', '/api/transactions/', token=TOKEN)
show("Semua transaksi (tanpa filter)", status, resp)

# Filter hanya pemasukan
status, resp = req('GET', '/api/transactions/', token=TOKEN, params={'type': 'income'})
show("Filter: hanya pemasukan (income)", status, resp)

# Filter hanya pengeluaran
status, resp = req('GET', '/api/transactions/', token=TOKEN, params={'type': 'expense'})
show("Filter: hanya pengeluaran (expense)", status, resp)

# Filter kategori
status, resp = req('GET', '/api/transactions/', token=TOKEN, params={'category': 'Makan'})
show("Filter: kategori Makan", status, resp)

# Filter kombinasi
status, resp = req('GET', '/api/transactions/', token=TOKEN,
                   params={'type': 'expense', 'category': 'Belanja'})
show("Filter: expense + kategori Belanja", status, resp)


# ================================================================
# TEST HAPUS TRANSAKSI
# ================================================================
divider("TEST HAPUS TRANSAKSI")

if created_ids:
    id_to_delete = created_ids[-1]
    status, resp = req('DELETE', f'/api/transactions/{id_to_delete}', token=TOKEN)
    show(f"Hapus transaksi #{id_to_delete}", status, resp)

    # Coba hapus lagi (seharusnya 404)
    status, resp = req('DELETE', f'/api/transactions/{id_to_delete}', token=TOKEN)
    show(f"Hapus transaksi #{id_to_delete} lagi (harus GAGAL 404)", status, resp, expect_success=False)

    # Coba hapus transaksi milik user lain (id=9999)
    status, resp = req('DELETE', '/api/transactions/9999', token=TOKEN)
    show("Hapus transaksi tidak ada (harus GAGAL 404)", status, resp, expect_success=False)


# ================================================================
# RINGKASAN AKHIR
# ================================================================
divider("DASHBOARD FINAL (setelah satu transaksi dihapus)")
status, resp = req('GET', '/api/transactions/dashboard', token=TOKEN)
show("Dashboard final", status, resp)

print("\n" + "="*60)
print("  Semua test selesai!")
print("="*60 + "\n")

