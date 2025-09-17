from flask import Flask, request, render_template, session, redirect, url_for, send_file
import io
import contextlib
import numpy as np
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Store the generated plot image in memory
plot_buffer = None

# Initialize history storage in the session
@app.before_request
def initialize_session():
    if "history" not in session:
        session["history"] = []

def safe_exec(user_code):
    global plot_buffer
    # Set a non-interactive backend for Matplotlib
    import matplotlib
    matplotlib.use('Agg')

    # Reset Matplotlib state for each execution
    plt.close('all')
    plot_buffer = None

    # Restricted globals and locals for sandbox
    allowed_globals = {
        "__builtins__": {
            "print": print,
            "len": len,
            "range": range,
            "int": int,
            "float": float,
            "str": str,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "abs": abs,
            "sum": sum,
            "__import__": __import__,
        },
        "np": np,
        "plt": plt,
    }
    allowed_locals = {}

    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(user_code, allowed_globals, allowed_locals)
        output = stdout.getvalue()

        # Check if a plot was generated
        if plt.get_fignums():
            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            plot_buffer = buf

        return output, None
    except Exception as e:
        return None, str(e)

@app.route("/", methods=["GET", "POST"])
def index():
    global plot_buffer
    if request.method == "POST":
        user_code = request.form.get("code", "")
        result, error = safe_exec(user_code)

        # Save to session history
        history_entry = {
            "code": user_code,
            "output": result,
            "error": error,
            "plot": bool(plot_buffer),
        }
        session["history"].append(history_entry)
        session.modified = True

        return redirect(url_for("index"))

    # Pass `enumerate` explicitly to the template
    return render_template("index.html", history=session["history"], enumerate=enumerate)


@app.route("/plot/<int:plot_id>")
def plot(plot_id):
    global plot_buffer
    if plot_id < len(session["history"]):
        entry = session["history"][plot_id]
        if entry.get("plot"):
            return send_file(plot_buffer, mimetype="image/png")
    return "No plot found", 404

if __name__ == "__main__":
    app.run(debug=True)
