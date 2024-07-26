from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from datetime import datetime
from app import app, mysql
from my_utils import hash_password, check_password
import logging  # Tambahkan impor logging
import cv2
import threading
from face_recognition_utils import recognize_faces, get_db_connection
from config import app, mysql  # Impor app dan mysql dari config.py



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
    


@app.route('/clear_log', methods=['POST'])
def clear_log():
    try:
        with open('app.log', 'w'):
            pass
        app.logger.info('Log cleared successfully.')
        return jsonify({'message': 'Log cleared successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error clearing log: {e}")
        return jsonify({'error': 'Failed to clear log'}), 500
    
    

@app.route('/')
@app.route('/<page>')
@app.route('/<page>/<act>')
def dashboard(page=None, act=None):
    if page == 'absen':
        if act is None:
            return render_template('guru/modul/absen/absensi_kelas.html')
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
        print("Data Mengajar:", data_mengajar)

        if data_guru:
            if content == 'guru_dashboard':
                return render_template('guru/modul/home.html', data=data_guru, mengajar=data_mengajar, current_year=current_year)
            elif content == 'jadwal':
                return render_template('guru/modul/jadwal/jadwal_mengajar.html', data=data_guru, mengajar=data_mengajar, current_year=current_year)
            # Fungsi lainnya bisa ditambahkan di sini sesuai kebutuhan
            # Contoh: elif content == 'informasi':
            #         return render_template('guru/modul/informasi.html')
            elif content == 'absen':
                # Misalnya, kirim class_name sebagai parameter ke template
                return render_template('guru/modul/absen/absensi_kelas.html', data=data_guru, mengajar=data_mengajar, current_year=current_year)
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

@app.route('/jadwal/<int:pelajaran>')
def jadwal_page(pelajaran):
    return f"Jadwal page for pelajaran {pelajaran}"

@app.route('/akun')
def akun_page():
    return render_template('modul/akun/akun.html')

@app.route('/guru')
def guru():
    return render_template('modul/home.html')


#fitur deteksi

capture_lock = threading.Lock()
video_capture = None

@app.before_request
def before_request():
    global video_capture
    with capture_lock:
        if video_capture is None or not video_capture.isOpened():
            video_capture = cv2.VideoCapture(0)
            if video_capture.isOpened():
                app.logger.info("Berhasil terhubung ke kamera laptop")
                video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                video_capture.set(cv2.CAP_PROP_POS_MSEC, 2000)
                

def gen_frames():
    global video_capture
    while True:
        with capture_lock:
            if video_capture is None or not video_capture.isOpened():
                app.logger.error("Video capture is not opened")
                continue
            
            ret, frame = video_capture.read()
        if not ret:
            app.logger.error("Failed to capture frame")
            break
        
        frame, labels = recognize_faces(frame)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            app.logger.error("Failed to encode frame")
            break
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/labels')
def get_labels():
    global video_capture
    with capture_lock:
        if video_capture is None or not video_capture.isOpened():
            app.logger.error("Video capture is not opened")
            return jsonify(labels=[])

        ret, frame = video_capture.read()
    
    if not ret:
        return jsonify(labels=[])

    _, face_info = recognize_faces(frame)
    labeled_info = []

    try:
        db_connection = get_db_connection()
        if db_connection.is_connected():
            cursor = db_connection.cursor()

            for label in face_info:
                if label['threshold_met']:
                    query = "SELECT ds.nis, ds.nm_siswa, k.no_kls " \
                            "FROM dt_siswa ds " \
                            "JOIN kelas k ON ds.kls = k.id_kls " \
                            "WHERE ds.nis = %s AND ds.kls = 1"
                    cursor.execute(query, (label['label'],))
                    result = cursor.fetchone()

                    if result:
                        nis, nm_siswa, no_kls = result
                        status = "hadir"
                    else:
                        nis = label['label']
                        nm_siswa = "Tidak Terdaftar"
                        no_kls = ""
                        status = "tidak terdaftar di kelas ini!"

                    labeled_info.append({
                        'nis': nis,
                        'nm_siswa': nm_siswa,
                        'no_kls': no_kls,
                        'status': status,
                        'distance': float(label['distance']),
                        'threshold_met': label['threshold_met']
                    })
                else:
                    labeled_info.append({
                        'nis': label['label'],
                        'nm_siswa': "Unknown",
                        'no_kls': "",
                        'status': "tidak terdaftar di sistem!",
                        'distance': float(label['distance']),
                        'threshold_met': label['threshold_met']
                    })

            return jsonify(labels=labeled_info)
        else:
            return jsonify(labels=[])
    except mysql.connector.Error as e:
        app.logger.error(f"Error connecting to database: {e}")
        return jsonify(labels=[])
    finally:
        if db_connection.is_connected():
            db_connection.close()


@app.route('/attendance_table')
def attendance_table():
    try:
        db_connection = get_db_connection()
        if db_connection.is_connected():
            cursor = db_connection.cursor(dictionary=True)
            query = """
                SELECT 
                    a.nis, 
                    a.name as nm_siswa, 
                    a.kls, 
                    a.status, 
                    DATE_FORMAT(a.date, '%Y-%m-%d %H:%i:%s') as date, 
                    k.no_kls, 
                    k.nm_kls,
                    a.image 
                FROM 
                    attendance a 
                    INNER JOIN kelas k ON a.kls = k.id_kls 
                ORDER BY 
                    a.date DESC
            """
            cursor.execute(query)
            records = cursor.fetchall()
            return render_template('attendance_table.html', attendance=records)
        else:
            return render_template('attendance_table.html', attendance=[])
    except mysql.connector.Error as e:
        app.logger.error(f"Error connecting to database: {e}")
        return render_template('attendance_table.html', attendance=[])
    finally:
        if 'db_connection' in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


# Endpoint untuk menyimpan label ke database 
@app.route('/save_label', methods=['POST'])
def save_label():
    try:
        data = request.json
        
        # Periksa apakah 'label_info', 'image_data', dan 'matching_in_progress' ada
        if 'label_info' not in data or 'image_data' not in data or 'matching_in_progress' not in data:
            app.logger.error('Data yang diterima tidak lengkap dalam permintaan')
            return jsonify({'error': 'Data tidak lengkap'}), 400
        
        label_info = data['label_info']
        image_data_base64 = data['image_data']
        matching_in_progress = data['matching_in_progress']
        
        # Jika pencocokan sedang berlangsung, jangan simpan data
        if matching_in_progress:
            app.logger.info('Pencocokan sedang berlangsung, tidak menyimpan data.')
            return jsonify({'message': 'Pencocokan sedang berlangsung, data tidak disimpan'}), 200

        # Tunggu selama 3 detik sebelum melanjutkan penyimpanan data
        time.sleep(1)

        current_date = datetime.now().date()
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for label_data in label_info:
            label = label_data.get('label')
            distance = label_data.get('distance', 0)
            threshold_met = label_data.get('threshold_met', False)

            if label is None:
                app.logger.error('label_info tidak valid dalam permintaan')
                continue

            if threshold_met:
                db_connection = get_db_connection()
                cursor = db_connection.cursor()

                try:
                    query = "SELECT nis, nm_siswa, kls FROM dt_siswa WHERE nis = %s AND kls = 1"
                    cursor.execute(query, (label,))
                    student_info = cursor.fetchone()

                    if student_info:
                        nis, nama, kls = student_info
                        status = 'hadir'
                    else:
                        app.logger.info(f"Siswa dengan NIS: {label} tidak terdaftar atau bukan dari kelas 1")
                        return jsonify({'error': 'NIS atau kelas tidak sesuai'}), 400
                        continue

                    # Periksa apakah sudah ada entri untuk nis ini hari ini
                    check_query = "SELECT * FROM attendance WHERE nis = %s AND DATE(date) = %s"
                    cursor.execute(check_query, (nis, current_date))
                    existing_record = cursor.fetchone()

                    if existing_record:
                        app.logger.info(f"Melewati catatan duplikat untuk nis: {nis} pada tanggal: {current_date}")
                        continue

                    # Simpan data gambar dalam format base64 sebagai LONGTEXT
                    insert_query = "INSERT INTO attendance (nis, name, kls, status, date, image) VALUES (%s, %s, %s, %s, %s, %s)"
                    cursor.execute(insert_query, (nis, nama, kls, status, current_datetime, image_data_base64))
                    db_connection.commit()

                    app.logger.info(f"Menyimpan kehadiran untuk nis: {nis} pada tanggal: {current_date}")

                except Exception as e:
                    app.logger.error(f"Kesalahan menyimpan data ke database: {e}")
                    db_connection.rollback()
                    return jsonify({'error': 'Gagal menyimpan label dan gambar'}), 500

                finally:
                    cursor.close()
                    db_connection.close()

        return jsonify({'message': 'Label dan gambar berhasil disimpan'}), 200

    except Exception as e:
        app.logger.error(f"Kesalahan memproses permintaan: {e}")
        return jsonify({'error': 'Terjadi kesalahan dalam pemrosesan permintaan'}), 500
