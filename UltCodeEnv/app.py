import os
import io
import base64
import contextlib
import sys
from flask import Flask, request, render_template, jsonify, redirect, url_for, session, flash
import numpy as np
import matplotlib
import sqlite3
import subprocess
import tempfile
import shutil
import secrets
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

#from app2 import DATABASE

matplotlib.use('Agg')  # Set non-interactive backend
import matplotlib.pyplot as plt

app = Flask(__name__)
#app.secret_key = os.urandom(24)
app.secret_key = 'dev-secret-key'
DATABASE = 'code_executer.db'


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.before_request
def create_tables():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            output TEXT,
            error TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function



def capture_plot():
    """Capture the current matplotlib figure as a base64 encoded image."""
    try:
        # Check if there are any figures
        if not plt.get_fignums():
            return None

        # Save plot to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)

        # Encode to base64
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        # Close the plot to free memory
        plt.close('all')

        return plot_base64
    except Exception as e:
        print(f"Plot capture error: {e}")
        plt.close('all')
        return None


def safe_exec(user_code):
    # Capture output and errors
    output = []
    error = None
    plot = None

    # Redirect stdout
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()

    try:
        # Execute the code in a restricted environment
        exec_locals = {
            'np': np,
            'plt': plt,
            'numpy': np,
            'matplotlib': matplotlib
        }

        # Execute the code
        exec(user_code, exec_locals)

        # Capture any print outputs
        output = redirected_output.getvalue()

        # Capture plot if generated
        plot = capture_plot()

    except Exception as e:
        error = str(e)
    finally:
        # Restore stdout
        sys.stdout = old_stdout

    return output, error, plot




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        if len(username) < 3 or len(password) < 8:
            flash('Username must be at least 3 characters and password at least 8 characters.')
            return render_template('register.html')

        try:
            db = get_db()
            db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                       (username, generate_password_hash(password)))
            db.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!')
        finally:
            db.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = username
            return redirect(url_for('index'))

        flash('Invalid username or password')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        code = request.form.get('code', '')
        output = None
        error = None

        if code:
            try:
                # Execute code in a temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_file = os.path.join(temp_dir, 'code.py')
                    with open(temp_file, 'w') as f:
                        f.write(code)

                    # Execute the code
                    result = subprocess.run(
                        ['python', temp_file],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        cwd=temp_dir
                    )

                    output = result.stdout
                    error = result.stderr

                # Save to database
                db = get_db()
                db.execute(
                    'INSERT INTO executions (user_id, code, output, error) VALUES (?, ?, ?, ?)',
                    (session['user_id'], code, output, error)
                )
                db.commit()
                db.close()

            except subprocess.TimeoutExpired:
                error = "Execution timed out"
            except Exception as e:
                error = str(e)
            finally:
                if error:
                    flash(error)

    # Get execution history
    db = get_db()
    history = db.execute('''
        SELECT code, output, error, timestamp 
        FROM executions 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
        LIMIT 10
    ''', (session['user_id'],)).fetchall()
    db.close()

    return render_template('index.html', history=history)



if __name__ == '__main__':
    app.run(debug=True)