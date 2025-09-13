import os
import io
import base64
import sys
import uuid
from datetime import datetime
from flask import Flask, request, render_template, jsonify, session, redirect, url_for
import numpy as np
import matplotlib

matplotlib.use('Agg')  # Set non-interactive backend
import matplotlib.pyplot as plt
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24)


def init_db():
    """Initialize SQLite database for users and code history"""
    conn = sqlite3.connect('code_executor.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS code_history (
        id TEXT PRIMARY KEY,
        username TEXT,
        code TEXT,
        output TEXT,
        error TEXT,
        plot TEXT,
        timestamp DATETIME,
        FOREIGN KEY(username) REFERENCES users(username)
    )''')

    conn.commit()
    conn.close()


def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def capture_plot():
    """Capture the current matplotlib figure as a base64 encoded image."""
    try:
        # Check if there are any figures
        if not plt.get_fignums():
            return None

        plt.gcf().set_size_inches(6, 4)  # Reduced size

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')  # Reduced DPI
        buf.seek(0)

        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        plt.close('all')
        return plot_base64
    except Exception as e:
        print(f"Plot capture error: {e}")
        plt.close('all')
        return None

def safe_exec(user_code):
    output = ""
    error = None
    plot = None
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    try:
        exec_locals = {
            'np': np,
            'plt': plt,
            'numpy': np,
            'matplotlib': matplotlib
        }
        exec(user_code, exec_locals)
        output = redirected_output.getvalue()
        plot = capture_plot()
    except Exception as e:
        error = str(e)
    finally:
        sys.stdout = old_stdout
    return output, error, plot


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('code_executor.db')
        c = conn.cursor()

        c.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                  (username, hash_password(password)))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('code_executor.db')
        c = conn.cursor()

        try:
            # Insert new user
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                      (username, hash_password(password)))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error='Username already exists')
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Logout route"""
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_code = request.form.get('code', '')
        output, error, plot = safe_exec(user_code)
        cell_id = str(uuid.uuid4())

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect('code_executor.db')
        c = conn.cursor()
        c.execute('''INSERT INTO code_history 
                     (id, username, code, output, error, plot, timestamp) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (cell_id, session['username'], user_code, output, error, plot, timestamp))
        conn.commit()

        c.execute('SELECT * FROM code_history WHERE username = ? ORDER BY timestamp DESC',
                  (session['username'],))
        code_history = c.fetchall()
        conn.close()

        return jsonify({
            'cell': {
                'id': cell_id,
                'code': user_code,
                'output': output,
                'error': error,
                'plot': plot,
                'timestamp': timestamp
            },
            'history': code_history
        })

    conn = sqlite3.connect('code_executor.db')
    c = conn.cursor()
    c.execute('SELECT * FROM code_history WHERE username = ? ORDER BY timestamp DESC',
              (session['username'],))
    code_history = c.fetchall()
    conn.close()

    return render_template('index.html', code_history=code_history)


@app.route('/clear_history', methods=['POST'])
def clear_history():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Not logged in"})

    conn = sqlite3.connect('code_executor.db')
    c = conn.cursor()
    c.execute('DELETE FROM code_history WHERE username = ?', (session['username'],))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})


if __name__ == '__main__':
    init_db()  
    app.run(debug=True)
