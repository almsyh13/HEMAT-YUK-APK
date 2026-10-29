# HSC Finance - Backend

Backend aplikasi pencatat keuangan menggunakan **Python + Flask + SQLite**.

## 📁 Struktur File

```
backend/
├── app.py              # File utama — entry point aplikasi
├── database.py         # Koneksi & inisialisasi database
├── auth_routes.py      # Endpoint autentikasi (login, register)
├── requirements.txt    # Daftar library yang dibutuhkan
└── finance_app.db      # File database SQLite (dibuat otomatis)
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

Server akan berjalan di `http://localhost:5000`

---

## 📡 API Endpoints (Minggu 1 - Autentikasi)

### `POST /api/auth/register`
Mendaftar akun baru.

**Request Body:**
```json
{
    "username": "hamka",
    "email": "hamka@gmail.com",
    "password": "rahasia123"
}
```

**Response Sukses (201):**
```json
{
    "success": true,
    "message": "Akun \"hamka\" berhasil dibuat! Silakan login."
}
```

---

### `POST /api/auth/login`
Login dan mendapatkan JWT token.

**Request Body:**
```json
{
    "username": "hamka",
    "password": "rahasia123"
}
```

**Response Sukses (200):**
```json
{
    "success": true,
    "message": "Login berhasil!",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
        "id": 1,
        "username": "hamka",
        "email": "hamka@gmail.com"
    }
}
```

---

### `GET /api/auth/me`
Mendapatkan informasi user yang sedang login.  
⚠️ **Butuh token!** Kirim header: `Authorization: Bearer <token>`

**Response Sukses (200):**
```json
{
    "success": true,
    "user": {
        "id": 1,
        "username": "hamka",
        "email": "hamka@gmail.com",
        "created_at": "2026-10-29 08:00:00"
    }
}
```

---

## 🔐 Cara Kerja JWT Token

```
1. User login → Backend verifikasi username & password
2. Backend buat JWT Token (berlaku 24 jam)
3. Token dikirim ke Frontend
4. Frontend simpan token (di localStorage)
5. Setiap request berikutnya, frontend kirim token di Header:
   Authorization: Bearer <token>
6. Backend validasi token → berikan akses
```

## 🧪 Testing dengan cURL

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"hamka","email":"hamka@gmail.com","password":"rahasia123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"hamka","password":"rahasia123"}'

# Get current user (ganti TOKEN dengan token dari login)
curl http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer TOKEN"
```
