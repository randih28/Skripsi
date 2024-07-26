from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

@app.route('/run_php_script')
def run_php_script():
    # Ganti dengan path ke skrip PHP Anda, pastikan untuk menggunakan raw string (awalan 'r')
    php_script_path = r'C:\Users\randi\Downloads\Compressed\absensiswa\template\index.php'

    # Jalankan skrip PHP menggunakan subprocess
    result = subprocess.run(['php', php_script_path], capture_output=True, text=True)

    # Ambil output dari skrip PHP jika diperlukan
    output = result.stdout

    return jsonify({'output': output})

if __name__ == '__main__':
    app.run(debug=True)
