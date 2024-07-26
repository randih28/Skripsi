from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import logging
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Ganti dengan secret key yang kuat

# Config database
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'datasiswa'

mysql = MySQL(app)

# Setup logging
logging.basicConfig(level=logging.DEBUG)

def hash_password(password):
    """Menghasilkan hash SHA1 dari password"""
    return hashlib.sha1(password.encode()).hexdigest()

def check_password(hashed_password, password):
    """Memeriksa apakah password yang diberikan cocok dengan hash"""
    return hashed_password == hashlib.sha1(password.encode()).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    level = request.form.get('level')

    logging.debug(f"Login attempt: username={username}, level={level}")

    cur = mysql.connection.cursor()
    user = None

    if level == '1':  # Guru
        cur.execute("SELECT * FROM tb_guru WHERE nip=%s AND status='Y'", (username,))
        user = cur.fetchone()
    elif level == '2':  # Siswa
        cur.execute("SELECT * FROM tb_siswa WHERE nis=%s AND status='1'", (username,))
        user = cur.fetchone()
    elif level == '3':  # Kepala Sekolah
        cur.execute("SELECT * FROM tb_kepsek WHERE nip=%s AND status='Y'", (username,))
        user = cur.fetchone()
    else:
        flash("Level tidak valid", 'danger')
        logging.debug("Invalid level")
        return redirect(url_for('index'))

    logging.debug(f"User fetched: {user}")

    if user and check_password(user[4], password):  # Membandingkan password dengan hash SHA1
        logging.debug("Password check passed")
        session['user_id'] = user[0]  # Menggunakan indeks numerik untuk ID
        session['user_level'] = level
        flash(f"Login berhasil, {user[2]}", 'success')  # Menggunakan indeks numerik untuk nama
        if level == '1':
            logging.debug("Redirecting to guru dashboard")
            session['guru'] = user[0]  # Simpan ID guru di session jika login sebagai guru
            return redirect(url_for('guru_dashboard'))
        elif level == '2':
            logging.debug("Redirecting to siswa dashboard")
            return redirect(url_for('siswa_dashboard'))
        elif level == '3':
            logging.debug("Redirecting to kepsek dashboard")
            return redirect(url_for('kepsek_dashboard'))
    else:
        logging.debug("Username / Password Salah")
        flash("Username / Password Salah", 'danger')
        return redirect(url_for('index'))

@app.route('/')
@app.route('/<page>')
@app.route('/<page>/<act>')
def dashboard(page=None, act=None):
    if page == 'absen':
        if act is None:
            return render_template('guru/modul/absen/absen_kelas.html')
        elif act == 'surat_view':
            return render_template('guru/modul/absen/view_surat_izin.html')
        elif act == 'konfirmasi':
            return render_template('guru/modul/absen/konfirmasi_izin.html')
        elif act == 'update':
            return render_template('guru/modul/absen/absen_kelas_update.html')
    elif page == 'rekap':
        if act is None:
            return render_template('guru/modul/rekap/rekap_absen.html')
    elif page == 'jadwal':
        if act is None:
            return render_template('guru/modul/jadwal/jadwal_mengajar.html')
    elif page == 'akun':
        return render_template('guru/modul/akun/akun.html')
    elif page is None:
        return render_template('guru/modul/home.html')
    else:
        return "<b>Tidak ada Halaman</b>"

@app.route('/guru')
def guru_dashboard():
    current_year = datetime.now().year
    if 'guru' in session:
        id_guru = session['guru']
        # Mengambil data guru dari database
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM tb_guru WHERE id_guru = %s', (id_guru,))
        data = cursor.fetchone()  # Mendapatkan satu baris data sebagai tuple atau dictionary

        # Mengambil data mengajar
        cursor.execute('''
            SELECT tb_mengajar.id_mengajar,tb_mengajar.hari, tb_mengajar.jam_mengajar, tb_mengajar.jamke, tb_master_mapel.mapel, tb_mkelas.nama_kelas 
            FROM tb_mengajar 
            INNER JOIN tb_master_mapel ON tb_mengajar.id_mapel = tb_master_mapel.id_mapel 
            INNER JOIN tb_mkelas ON tb_mengajar.id_mkelas = tb_mkelas.id_mkelas 
            INNER JOIN tb_semester ON tb_mengajar.id_semester = tb_semester.id_semester 
            INNER JOIN tb_thajaran ON tb_mengajar.id_thajaran = tb_thajaran.id_thajaran 
            WHERE tb_mengajar.id_guru = %s AND tb_thajaran.status = 1
        ''', (id_guru,))
        mengajar = cursor.fetchall()  # Mendapatkan semua baris data

        cursor.close()

        if data:
            print(data)  # Menampilkan data guru di konsol Flask
            print(mengajar)  # Menampilkan data guru di konsol Flask
            return render_template('guru/index.html', data=data, mengajar=mengajar, current_year=current_year, default_content='guru/modul/home.html', jadwal='guru/modul/jadwal/jadwal_mengajar.html')
        else:
            flash('Data guru tidak ditemukan', 'danger')
            return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))  # Redirect ke halaman login jika tidak ada sesi guru
    

@app.route('/load_content')
def load_content():
    content = request.args.get('content', 'default_content')
    current_year = datetime.now().year

    if 'guru' in session:
        id_guru = session['guru']
        cursor = mysql.connection.cursor()
        
        # Query untuk mengambil data guru
        cursor.execute('SELECT * FROM tb_guru WHERE id_guru = %s', (id_guru,))
        data_guru = cursor.fetchone()  # Mendapatkan satu baris data guru
        
        # Query untuk mengambil data mengajar
        cursor.execute('''
            SELECT tb_mengajar.id_mengajar,tb_mengajar.hari, tb_mengajar.jam_mengajar, tb_mengajar.jamke, tb_master_mapel.mapel, tb_mkelas.nama_kelas 
            FROM tb_mengajar 
            INNER JOIN tb_master_mapel ON tb_mengajar.id_mapel = tb_master_mapel.id_mapel 
            INNER JOIN tb_mkelas ON tb_mengajar.id_mkelas = tb_mkelas.id_mkelas 
            INNER JOIN tb_semester ON tb_mengajar.id_semester = tb_semester.id_semester 
            INNER JOIN tb_thajaran ON tb_mengajar.id_thajaran = tb_thajaran.id_thajaran 
            WHERE tb_mengajar.id_guru = %s AND tb_thajaran.status = 1
        ''', (id_guru,))
        data_mengajar = cursor.fetchall()  # Mendapatkan semua baris data mengajar
        
        cursor.close()
        
        if data_guru:
            if content == 'guru_dashboard':
                return render_template('guru/modul/home.html', data=data_guru, mengajar=data_mengajar, current_year=current_year)
            elif content == 'jadwal':
                return render_template('guru/modul/jadwal/jadwal_mengajar.html', data=data_guru, mengajar=data_mengajar, current_year=current_year)
            # Fungsi lainnya bisa ditambahkan di sini sesuai kebutuhan
            # Contoh: elif content == 'informasi':
            #         return render_template('guru/modul/informasi.html')
        else:
            flash('Data guru tidak ditemukan', 'danger')
            return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))
    
    # Jika tidak ada sesi guru atau content tidak ditemukan
    return render_template('guru/modul/home.html', data=data_guru, mengajar=data_mengajar, current_year=current_year)


@app.route('/')
def home():
    return render_template('modul/home.html')

@app.route('/absen/<int:pelajaran>')
def absen_page(pelajaran):
    return f"Absen page for pelajaran {pelajaran}"

@app.route('/rekap/<int:pelajaran>')
def rekap_page(pelajaran):
    return f"Rekap page for pelajaran {pelajaran}"

@app.route('/rekap')
def rekap():
    act = request.args.get('act', '')
    if act == '':
        return render_template('modul/rekap/rekap_absen.html')
    else:
        return "<b>Action not found</b>"

@app.route('/jadwal')
def jadwal():
    act = request.args.get('act', '')
    if act == '':
        return render_template('guru/modul/jadwal/jadwal_mengajar.html')
    else:
        return "<b>Action not found</b>"

@app.route('/akun')
def akun():
    return render_template('modul/akun/akun.html')



@app.route('/siswa')
def siswa_dashboard():
    if 'user_id' in session and session['user_level'] == '2':
        return "Siswa Dashboard"
    else:
        flash("Anda harus login sebagai Siswa untuk mengakses halaman ini", 'danger')
        logging.debug("Unauthorized access to siswa dashboard")
        return redirect(url_for('index'))

@app.route('/kepsek')
def kepsek_dashboard():
    if 'user_id' in session and session['user_level'] == '3':
        return "Kepala Sekolah Dashboard"
    else:
        flash("Anda harus login sebagai Kepala Sekolah untuk mengakses halaman ini", 'danger')
        logging.debug("Unauthorized access to kepsek dashboard")
        return redirect(url_for('index'))
    

@app.route('/logout')
def logout():
    # Lakukan proses logout di sini, seperti menghapus sesi atau data lainnya
    session.pop('user_id', None)
    session.pop('user_level', None)
    session.pop('guru', None)
    flash('Anda telah berhasil logout', 'success')
    return redirect(url_for('index'))


@app.route('/jadwal_mengajar')
def jadwal_mengajar():
    if 'guru' in session:
        id_guru = session['guru']
        cursor = mysql.connection.cursor()
        cursor.execute('''
            SELECT tb_mengajar.id_mengajar, tb_master_mapel.mapel, tb_mkelas.nama_kelas, tb_semester.semester,tb_mengajar.hari, tb_mengajar.jamke, tb_mengajar.jam_mengajar
            FROM tb_mengajar
            INNER JOIN tb_master_mapel ON tb_mengajar.id_mapel = tb_master_mapel.id_mapel
            INNER JOIN tb_mkelas ON tb_mengajar.id_mkelas = tb_mkelas.id_mkelas
            INNER JOIN tb_semester ON tb_mengajar.id_semester = tb_semester.id_semester
            INNER JOIN tb_thajaran ON tb_mengajar.id_thajaran = tb_thajaran.id_thajaran
            WHERE tb_mengajar.id_guru = %s AND tb_thajaran.status = 1
        ''', (id_guru,))
        mengajar = cursor.fetchall()
        cursor.close()

        print(mengajar)  # Menampilkan data ke konsol Flask

        return render_template('guru/modul/jadwal/jadwal_mengajar.html', mengajar=mengajar)
    else:
        flash("Anda harus login sebagai Guru untuk mengakses halaman ini", 'danger')
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
