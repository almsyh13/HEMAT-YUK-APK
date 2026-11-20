"""
transaction_routes.py
---------------------
File ini berisi semua ENDPOINT yang berhubungan dengan transaksi keuangan:

  POST   /api/transactions/             -> Tambah transaksi baru
  GET    /api/transactions/             -> Riwayat transaksi (dengan filter)
  GET    /api/transactions/dashboard    -> Data dashboard (saldo, pemasukan, pengeluaran)
  DELETE /api/transactions/<id>         -> Hapus satu transaksi

Konsep PENTING yang baru di file ini:
  - @jwt_required()     : Semua endpoint wajib login (ada token)
  - get_jwt_identity()  : Ambil user_id dari token JWT
  - Query Parameter     : Filter yang dikirim di URL, contoh:
                          /api/transactions/?type=income&category=Gaji
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection

# Blueprint untuk kelompok endpoint transaksi
transaction_bp = Blueprint('transactions', __name__)

# ============================================================
# Daftar kategori yang diizinkan (sama dengan frontend)
# ============================================================
INCOME_CATEGORIES  = ['Gaji', 'Freelance', 'Investasi', 'Hadiah', 'Lainnya']
EXPENSE_CATEGORIES = ['Makan', 'Transportasi', 'Belanja', 'Tagihan',
                      'Hiburan', 'Kesehatan', 'Pendidikan', 'Lainnya']


# ================================================================
# ENDPOINT 1: TAMBAH TRANSAKSI BARU
# POST /api/transactions/
# ================================================================
@transaction_bp.route('/', methods=['POST'])
@jwt_required()
def add_transaction():
    """
    Menambah transaksi baru (pemasukan atau pengeluaran).

    Frontend mengirim JSON:
    {
        "type":             "income",        <- 'income' atau 'expense'
        "amount":           500000,          <- nominal dalam rupiah (angka)
        "category":         "Gaji",          <- kategori transaksi
        "description":      "Gaji Oktober",  <- catatan/detail (opsional)
        "transaction_date": "2026-11-11"     <- tanggal (format YYYY-MM-DD)
    }

    Alur:
    1. Ambil user_id dari token JWT (siapa yang sedang login)
    2. Ambil & validasi data dari request body
    3. Simpan ke tabel transactions
    4. Kembalikan data transaksi yang baru dibuat
    """

    # Langkah 1: Ambil user_id dari token
    # get_jwt_identity() mengembalikan nilai 'identity' yang kita set saat login
    current_user_id = get_jwt_identity()

    # Langkah 2: Ambil data dari request body
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Request body kosong'}), 400

    transaction_type = data.get('type', '').strip().lower()
    amount           = data.get('amount')
    category         = data.get('category', '').strip()
    description      = data.get('description', '').strip()
    transaction_date = data.get('transaction_date', '').strip()

    # --- Validasi field wajib ---
    if not transaction_type or amount is None or not category or not transaction_date:
        return jsonify({
            'success': False,
            'message': 'Field type, amount, category, dan transaction_date wajib diisi'
        }), 400

    # --- Validasi jenis transaksi ---
    if transaction_type not in ('income', 'expense'):
        return jsonify({
            'success': False,
            'message': 'Jenis transaksi harus "income" (pemasukan) atau "expense" (pengeluaran)'
        }), 400

    # --- Validasi nominal ---
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({
            'success': False,
            'message': 'Nominal harus berupa angka dan lebih dari 0'
        }), 400

    # --- Validasi kategori sesuai jenis transaksi ---
    valid_categories = INCOME_CATEGORIES if transaction_type == 'income' else EXPENSE_CATEGORIES
    if category not in valid_categories:
        return jsonify({
            'success': False,
            'message': f'Kategori "{category}" tidak valid untuk jenis "{transaction_type}". '
                       f'Pilihan: {", ".join(valid_categories)}'
        }), 400

    # Langkah 3: Simpan ke database
    conn   = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, category, description, transaction_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (current_user_id, transaction_type, amount, category, description, transaction_date))

    # lastrowid = id dari baris yang baru saja dimasukkan
    new_id = cursor.lastrowid
    conn.commit()

    # Ambil data yang baru dibuat untuk dikembalikan ke frontend
    cursor.execute('SELECT * FROM transactions WHERE id = ?', (new_id,))
    new_transaction = cursor.fetchone()
    conn.close()

    # Langkah 4: Response sukses
    return jsonify({
        'success': True,
        'message': 'Transaksi berhasil disimpan!',
        'transaction': _format_transaction(new_transaction)
    }), 201


# ================================================================
# ENDPOINT 2: DASHBOARD (Saldo, Total Pemasukan, Total Pengeluaran)
# GET /api/transactions/dashboard
# ================================================================
@transaction_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """
    Mengambil ringkasan keuangan untuk halaman dashboard:
      - total_income    : total semua pemasukan
      - total_expense   : total semua pengeluaran
      - balance         : sisa saldo (pemasukan - pengeluaran)
      - income_count    : jumlah transaksi pemasukan
      - expense_count   : jumlah transaksi pengeluaran

    Data ini REAL-TIME karena dihitung langsung dari database setiap kali
    endpoint ini dipanggil — tidak ada cache.

    Konsep SQL yang digunakan:
      SUM(amount)  = menjumlahkan semua nilai di kolom amount
      COALESCE(x, 0) = jika x NULL (tidak ada data), gunakan 0
      WHERE type = 'income' = filter hanya pemasukan
    """

    current_user_id = get_jwt_identity()
    conn   = get_db_connection()
    cursor = conn.cursor()

    # Hitung total pemasukan
    cursor.execute('''
        SELECT
            COALESCE(SUM(amount), 0) AS total,
            COUNT(*)                 AS count
        FROM transactions
        WHERE user_id = ? AND type = 'income'
    ''', (current_user_id,))
    income_row = cursor.fetchone()

    # Hitung total pengeluaran
    cursor.execute('''
        SELECT
            COALESCE(SUM(amount), 0) AS total,
            COUNT(*)                 AS count
        FROM transactions
        WHERE user_id = ? AND type = 'expense'
    ''', (current_user_id,))
    expense_row = cursor.fetchone()

    conn.close()

    total_income  = income_row['total']
    total_expense = expense_row['total']
    balance       = total_income - total_expense   # Sisa saldo = pemasukan - pengeluaran

    return jsonify({
        'success': True,
        'dashboard': {
            'balance':       balance,          # Sisa saldo
            'total_income':  total_income,     # Total pemasukan
            'total_expense': total_expense,    # Total pengeluaran
            'income_count':  income_row['count'],   # Jumlah transaksi masuk
            'expense_count': expense_row['count'],  # Jumlah transaksi keluar
        }
    }), 200


# ================================================================
# ENDPOINT 3: RIWAYAT TRANSAKSI (dengan filter)
# GET /api/transactions/
# GET /api/transactions/?type=income
# GET /api/transactions/?category=Gaji
# GET /api/transactions/?type=expense&category=Makan
# ================================================================
@transaction_bp.route('/', methods=['GET'])
@jwt_required()
def get_transactions():
    """
    Mengambil daftar riwayat transaksi milik user yang login.

    Filter bisa dikirim sebagai QUERY PARAMETER di URL:
      ?type=income          -> hanya tampilkan pemasukan
      ?type=expense         -> hanya tampilkan pengeluaran
      ?category=Gaji        -> hanya transaksi kategori Gaji
      ?type=income&category=Gaji  -> kombinasi keduanya

    Konsep Query Parameter:
      URL: /api/transactions/?type=income&category=Gaji
      Flask membacanya dengan: request.args.get('type')

    Konsep SQL dinamis:
      Kita bangun query WHERE secara dinamis berdasarkan filter yang dikirim.
      Ini lebih aman dan fleksibel daripada menulis banyak IF-ELSE.
    """

    current_user_id = get_jwt_identity()

    # Ambil filter dari query parameter URL
    filter_type     = request.args.get('type', '').strip().lower()
    filter_category = request.args.get('category', '').strip()

    # ---- Bangun query SQL secara dinamis ----
    # Mulai dengan kondisi dasar: hanya data milik user ini
    query  = 'SELECT * FROM transactions WHERE user_id = ?'
    params = [current_user_id]

    # Tambahkan filter type jika ada
    if filter_type in ('income', 'expense'):
        query  += ' AND type = ?'
        params.append(filter_type)

    # Tambahkan filter category jika ada
    if filter_category:
        query  += ' AND category = ?'
        params.append(filter_category)

    # Urutkan dari yang terbaru
    query += ' ORDER BY transaction_date DESC, created_at DESC'

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Ubah hasil query menjadi list of dict (agar bisa dijadikan JSON)
    transactions = [_format_transaction(row) for row in rows]

    return jsonify({
        'success': True,
        'count':        len(transactions),
        'filters': {
            'type':     filter_type     or 'semua',
            'category': filter_category or 'semua',
        },
        'transactions': transactions
    }), 200


# ================================================================
# ENDPOINT 4: HAPUS TRANSAKSI
# DELETE /api/transactions/<transaction_id>
# ================================================================
@transaction_bp.route('/<int:transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    """
    Menghapus satu transaksi berdasarkan ID-nya.

    <int:transaction_id> di URL = parameter dinamis.
    Contoh: DELETE /api/transactions/5  -> hapus transaksi dengan id=5

    PENTING: Kita pastikan transaksi itu MILIK user yang login,
    bukan milik user lain! (Validasi kepemilikan)
    """

    current_user_id = get_jwt_identity()
    conn   = get_db_connection()
    cursor = conn.cursor()

    # Cari transaksi — pastikan milik user yang sedang login
    cursor.execute(
        'SELECT * FROM transactions WHERE id = ? AND user_id = ?',
        (transaction_id, current_user_id)
    )
    transaction = cursor.fetchone()

    if transaction is None:
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Transaksi tidak ditemukan atau bukan milik Anda'
        }), 404

    # Hapus transaksi
    cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f'Transaksi #{transaction_id} berhasil dihapus'
    }), 200


# ================================================================
# ENDPOINT 5: DAFTAR KATEGORI (untuk isi dropdown di frontend)
# GET /api/transactions/categories
# ================================================================
@transaction_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """
    Mengembalikan daftar kategori yang tersedia,
    dipisah antara pemasukan dan pengeluaran.
    Frontend bisa pakai ini untuk mengisi dropdown kategori.
    """
    return jsonify({
        'success': True,
        'categories': {
            'income':  INCOME_CATEGORIES,
            'expense': EXPENSE_CATEGORIES
        }
    }), 200


# ================================================================
# HELPER FUNCTION (Fungsi Pembantu)
# ================================================================
def _format_transaction(row):
    """
    Mengubah satu baris hasil query SQLite menjadi dictionary Python.
    Fungsi ini dipakai berulang kali, jadi kita buat sebagai helper.

    Awalan _ (underscore) menandakan fungsi ini hanya untuk pemakaian
    internal di file ini — bukan untuk diakses dari luar.
    """
    return {
        'id':               row['id'],
        'type':             row['type'],          # 'income' atau 'expense'
        'amount':           row['amount'],
        'category':         row['category'],
        'description':      row['description'],
        'transaction_date': row['transaction_date'],
        'created_at':       row['created_at'],
    }

