# HSC Finance — Backend API

Backend aplikasi pencatat keuangan menggunakan **Python + Flask + SQLite**.

## 📁 Struktur File

```
backend/
├── app.py                  # File utama — entry point aplikasi
├── database.py             # Koneksi & inisialisasi database
├── auth_routes.py          # Endpoint autentikasi (login, register)
├── transaction_routes.py   # Endpoint transaksi (dashboard, tambah, riwayat, hapus)
├── test_api.py             # Script test endpoint autentikasi
├── test_transactions.py    # Script test endpoint transaksi
├── requirements.txt        # Daftar library yang dibutuhkan
└── finance_app.db          # File database SQLite (dibuat otomatis)
```

## 🚀 Cara Menjalankan

### 1. Install dependencies (hanya perlu sekali)
```bash
pip install -r requirements.txt
```

### 2. Jalankan server
```bash
python app.py
```

Server berjalan di `http://localhost:5000`

### 3. Jalankan test (opsional, di terminal lain)
```bash
python test_api.py          # Test autentikasi
python test_transactions.py # Test transaksi
```

---

## 🗄️ Skema Database

```
users
├── id            INTEGER  PK AUTOINCREMENT
├── username      TEXT     UNIQUE NOT NULL
├── email         TEXT     UNIQUE NOT NULL
├── password      TEXT     NOT NULL  ← disimpan sebagai HASH, bukan teks biasa
└── created_at    TEXT     DEFAULT now

transactions
├── id                INTEGER  PK AUTOINCREMENT
├── user_id           INTEGER  FK → users.id
├── type              TEXT     'income' | 'expense'
├── amount            REAL     > 0
├── category          TEXT     NOT NULL
├── description       TEXT     (opsional)
├── transaction_date  TEXT     format YYYY-MM-DD
└── created_at        TEXT     DEFAULT now
```

---

## 📡 API Endpoints

> Semua endpoint transaksi **wajib menyertakan JWT Token** di header:
> ```
> Authorization: Bearer <token_dari_login>
> ```

---

### 🔐 AUTENTIKASI

#### `POST /api/auth/register` — Daftar akun baru
**Request Body:**
```json
{
    "username": "hamka",
    "email":    "hamka@gmail.com",
    "password": "rahasia123"
}
```
**Response `201`:**
```json
{ "success": true, "message": "Akun \"hamka\" berhasil dibuat! Silakan login." }
```

---

#### `POST /api/auth/login` — Login
**Request Body:**
```json
{ "username": "hamka", "password": "rahasia123" }
```
**Response `200`:**
```json
{
    "success": true,
    "token":   "eyJhbGci...",
    "user":    { "id": 1, "username": "hamka", "email": "hamka@gmail.com" }
}
```

---

#### `GET /api/auth/me` — Info user yang sedang login
**Response `200`:**
```json
{
    "success": true,
    "user": { "id": 1, "username": "hamka", "email": "hamka@gmail.com", "created_at": "..." }
}
```

---

### 💰 TRANSAKSI

#### `GET /api/transactions/dashboard` — Data dashboard real-time
**Response `200`:**
```json
{
    "success": true,
    "dashboard": {
        "balance":       3220000,
        "total_income":  3500000,
        "total_expense": 280000,
        "income_count":  2,
        "expense_count": 3
    }
}
```

---

#### `POST /api/transactions/` — Tambah transaksi baru
**Request Body:**
```json
{
    "type":             "income",
    "amount":           3000000,
    "category":         "Gaji",
    "description":      "Gaji Oktober",
    "transaction_date": "2026-11-01"
}
```
**Response `201`:**
```json
{
    "success": true,
    "message": "Transaksi berhasil disimpan!",
    "transaction": {
        "id": 1, "type": "income", "amount": 3000000.0,
        "category": "Gaji", "description": "Gaji Oktober",
        "transaction_date": "2026-11-01", "created_at": "..."
    }
}
```

**Kategori yang valid:**

| Jenis | Kategori |
|---|---|
| `income`  | Gaji, Freelance, Investasi, Hadiah, Lainnya |
| `expense` | Makan, Transportasi, Belanja, Tagihan, Hiburan, Kesehatan, Pendidikan, Lainnya |

---

#### `GET /api/transactions/` — Riwayat transaksi
Mendukung **filter via query parameter**:

| Parameter | Contoh | Keterangan |
|---|---|---|
| `type` | `?type=income` | Filter jenis transaksi |
| `category` | `?category=Gaji` | Filter kategori |
| Kombinasi | `?type=expense&category=Makan` | Keduanya sekaligus |

**Response `200`:**
```json
{
    "success": true,
    "count": 2,
    "filters": { "type": "income", "category": "semua" },
    "transactions": [ { "id": 1, "type": "income", ... }, ... ]
}
```

---

#### `GET /api/transactions/categories` — Daftar kategori
**Response `200`:**
```json
{
    "success": true,
    "categories": {
        "income":  ["Gaji", "Freelance", "Investasi", "Hadiah", "Lainnya"],
        "expense": ["Makan", "Transportasi", "Belanja", "Tagihan", "Hiburan", "Kesehatan", "Pendidikan", "Lainnya"]
    }
}
```

---

#### `DELETE /api/transactions/<id>` — Hapus transaksi
Contoh: `DELETE /api/transactions/5`

**Response `200`:**
```json
{ "success": true, "message": "Transaksi #5 berhasil dihapus" }
```

---

## 🔐 Cara Kerja JWT Token

```
1. User login  →  Backend verifikasi username & password
2. Backend buat JWT Token (berlaku 24 jam)
3. Token dikirim ke Frontend
4. Frontend simpan token (di localStorage / state)
5. Setiap request berikutnya, frontend kirim token di Header:
       Authorization: Bearer <token>
6. Backend validasi token → berikan akses ke data
```

## ⚠️ HTTP Status Code yang Digunakan

| Kode | Arti | Contoh |
|---|---|---|
| `200` | OK — request berhasil | Login, ambil data |
| `201` | Created — data baru berhasil dibuat | Register, tambah transaksi |
| `400` | Bad Request — data yang dikirim salah/tidak lengkap | Nominal negatif, field kosong |
| `401` | Unauthorized — belum login atau token tidak valid | Akses tanpa token |
| `404` | Not Found — data tidak ditemukan | Hapus transaksi yang tidak ada |
| `409` | Conflict — terjadi duplikasi data | Register username yang sudah ada |
