import os
import io
import base64
import sys
import uuid
from flask import Flask, request, render_template, jsonify
import numpy as np
import matplotlib

matplotlib.use('Agg')  
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = os.urandom(24)

CODE_HISTORY = []

def capture_plot():
    """Capture the current matplotlib figure as a base64 encoded image."""
    try:
        if not plt.get_fignums():
            return None

        # Save plot to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_code = request.form.get('code', '')

        output, error, plot = safe_exec(user_code)

        cell_id = str(uuid.uuid4())

        code_cell = {
            'id': cell_id,
            'code': user_code,
            'output': output,
            'error': error,
            'plot': plot
        }

        CODE_HISTORY.append(code_cell)

        return jsonify({
            'cell': code_cell,
            'history': CODE_HISTORY
        })

    return render_template('index.html', code_history=CODE_HISTORY)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    global CODE_HISTORY
    CODE_HISTORY = []
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
