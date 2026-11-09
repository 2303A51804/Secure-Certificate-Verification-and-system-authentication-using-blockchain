
from flask import Flask, request, redirect, url_for, render_template_string
import sqlite3
import hashlib
import json

app = Flask(__name__)
DB_NAME = "certificates.db"


# Create database and table
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                certificate_id TEXT PRIMARY KEY,
                student_name TEXT NOT NULL,
                course TEXT NOT NULL,
                institution TEXT NOT NULL,
                certificate_hash TEXT NOT NULL
            )
        """)


# Generate SHA-256 certificate hash
def generate_hash(cert_id, name, course, institution):
    details = {
        "certificate_id": cert_id.strip(),
        "student_name": name.strip(),
        "course": course.strip(),
        "institution": institution.strip()
    }

    data = json.dumps(
        details, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# HTML page
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Certificate Verification System</title>
    <style>
        body {
            font-family: Arial;
            background: #eef3f9;
            margin: 0;
            padding: 25px;
        }
        h1 {
            text-align: center;
            color: #123b70;
        }
        .container {
            max-width: 650px;
            margin: auto;
        }
        .card {
            background: white;
            padding: 22px;
            margin: 20px 0;
            border-radius: 12px;
            box-shadow: 0 3px 12px #0001;
        }
        input {
            width: 95%;
            padding: 10px;
            margin: 7px 0 12px;
        }
        button {
            background: #1764b0;
            color: white;
            padding: 11px 18px;
            border: none;
            cursor: pointer;
            border-radius: 5px;
        }
        .valid { color: green; }
        .invalid { color: red; }
        .hash { overflow-wrap: anywhere; font-size: 13px; }
    </style>
</head>
<body>
    <h1>Secure Certificate Verification</h1>

    <div class="container">
        <div class="card">
            <h2>Register Certificate</h2>
            <form method="POST" action="/register">
                <label>Certificate ID</label>
                <input name="cert_id" required
                       placeholder="CERT001">

                <label>Student Name</label>
                <input name="name" required
                       placeholder="Student name">

                <label>Course</label>
                <input name="course" required
                       placeholder="B.Tech CSE">

                <label>Institution</label>
                <input name="institution" required
                       placeholder="University name">

                <button type="submit">Register Certificate</button>
            </form>
        </div>

        <div class="card">
            <h2>Verify Certificate</h2>
            <form method="POST" action="/verify">
                <label>Certificate ID</label>
                <input name="cert_id" required
                       placeholder="Enter Certificate ID">
                <button type="submit">Verify Certificate</button>
            </form>

            {% if result %}
                <h3 class="{{ 'valid' if result.valid else 'invalid' }}">
                    {{ result.message }}
                </h3>

                {% if result.name %}
                    <p><b>Student:</b> {{ result.name }}</p>
                    <p><b>Course:</b> {{ result.course }}</p>
                    <p><b>Institution:</b> {{ result.institution }}</p>
                    <p><b>SHA-256 Hash:</b></p>
                    <p class="hash">{{ result.hash }}</p>
                {% endif %}
            {% endif %}
        </div>
    </div>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML, result=None)


# Register certificate
@app.route("/register", methods=["POST"])
def register():
    cert_id = request.form["cert_id"].strip()
    name = request.form["name"].strip()
    course = request.form["course"].strip()
    institution = request.form["institution"].strip()

    if not all([cert_id, name, course, institution]):
        return "All fields are required.", 400

    digest = generate_hash(cert_id, name, course, institution)

    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                INSERT INTO certificates
                VALUES (?, ?, ?, ?, ?)
            """, (cert_id, name, course, institution, digest))

        return """
        <h2 style='color:green'>Certificate registered successfully!</h2>
        <a href='/'>Go back</a>
        """
    except sqlite3.IntegrityError:
        return """
        <h2 style='color:red'>Certificate ID already exists!</h2>
        <a href='/'>Go back</a>
        """


# Verify certificate
@app.route("/verify", methods=["POST"])
def verify():
    cert_id = request.form["cert_id"].strip()

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        record = conn.execute("""
            SELECT * FROM certificates WHERE certificate_id = ?
        """, (cert_id,)).fetchone()

    if record is None:
        result = {
            "valid": False,
            "message": "INVALID: Certificate not found."
        }
    else:
        current_hash = generate_hash(
            record["certificate_id"],
            record["student_name"],
            record["course"],
            record["institution"]
        )

        valid = current_hash == record["certificate_hash"]

        result = {
            "valid": valid,
            "message": (
                "VALID: Record integrity verified."
                if valid else
                "INVALID: Record integrity check failed."
            ),
            "name": record["student_name"],
            "course": record["course"],
            "institution": record["institution"],
            "hash": record["certificate_hash"]
        }

    return render_template_string(HTML, result=result)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
