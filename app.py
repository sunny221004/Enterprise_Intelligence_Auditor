
from ai_engine import analyze_impact
from contextlib import contextmanager
from flask import (
    Flask, render_template, request,
    jsonify, redirect, url_for, session, flash
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from werkzeug.utils import secure_filename
from functools import wraps
from PyPDF2 import PdfReader
from docx import Document
from difflib import unified_diff, SequenceMatcher
import sqlite3
import io
import os
import json

app = Flask(__name__)

# SECURITY CONFIGURATION
app.secret_key = os.environ.get(
    "SECRET_KEY", "development-only-change-this-secret"
)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True

# SECURITY CONFIGURATION
app.secret_key = os.environ.get(
    "SECRET_KEY", "development-only-change-this-secret"
)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "false").lower() == "true"
)

DATABASE = "enterprise_auditor.db"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


# ---------------------------------
# DATABASE CONNECTION
# ---------------------------------


@contextmanager
def get_db():

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def init_db():

    with get_db() as db:

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                activity TEXT NOT NULL,
                filename TEXT,
                risk_level TEXT,
                risk_score INTEGER,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)


init_db()


# ---------------------------------
# AUTHENTICATION
# ---------------------------------

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "Please login first."
                }), 401

            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


@app.route("/setup", methods=["GET", "POST"])
def setup():

    with get_db() as db:
        user_count = db.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

    if user_count > 0:
        return redirect(url_for("login"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or len(password) < 8:
            flash("Enter all details. Password must be at least 8 characters.")
            return redirect(url_for("setup"))

        with get_db() as db:
            try:
                cursor = db.execute("""
                    INSERT INTO users
                    (username, email, password, role)
                    VALUES (?, ?, ?, 'admin')
                """, (
                    username,
                    email,
                    generate_password_hash(password)
                ))

                session.clear()
                session["user_id"] = cursor.lastrowid
                session["username"] = username
                session["role"] = "admin"

                return redirect(url_for("home"))

            except sqlite3.IntegrityError:
                flash("Username or email already exists.")
                return redirect(url_for("setup"))

    return render_template("setup.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    with get_db() as db:
        count = db.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

    if count == 0:
        return redirect(url_for("setup"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as db:
            user = db.execute("""
                SELECT * FROM users
                WHERE username = ?
            """, (username,)).fetchone()

        if user and check_password_hash(
            user["password"], password
        ):

            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():

    session.clear()
    return redirect(url_for("login"))


# ---------------------------------
# DOCUMENT UTILITIES
# ---------------------------------

def allowed_file(filename):

    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def extract_text(file):

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[1].lower()

    content = file.read()

    if extension == "txt":
        return content.decode(
            "utf-8-sig", errors="replace"
        )

    elif extension == "pdf":

        reader = PdfReader(io.BytesIO(content))

        if reader.is_encrypted:
            raise ValueError("Encrypted PDF is not supported.")

        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif extension == "docx":

        document = Document(io.BytesIO(content))

        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    return ""


# ---------------------------------
# RISK ASSESSMENT
# ---------------------------------

def assess_risk(text):

    text = text.lower()

    high_keywords = [
        "security breach", "data loss",
        "unauthorized access", "termination",
        "compliance violation", "critical failure",
        "confidential data", "legal penalty"
    ]

    medium_keywords = [
        "policy change", "salary", "attendance",
        "workflow", "approval", "employee",
        "database", "access control"
    ]

    high_count = sum(
        text.count(word) for word in high_keywords
    )

    medium_count = sum(
        text.count(word) for word in medium_keywords
    )

    score = min(
        100, high_count * 25 + medium_count * 10
    )

    if score >= 50:
        level = "High"
    elif score >= 20:
        level = "Medium"
    else:
        level = "Low"

    return {
        "score": score,
        "level": level,
        "high_matches": high_count,
        "medium_matches": medium_count
    }


# ---------------------------------
# DEPARTMENT DETECTION
# ---------------------------------

def detect_departments(text):

    text = text.lower()

    keywords = {
        "Human Resources": [
            "employee", "salary", "attendance",
            "recruitment", "leave", "hr"
        ],
        "Information Technology": [
            "software", "database", "server",
            "security", "network", "system"
        ],
        "Finance": [
            "budget", "payment", "invoice",
            "financial", "salary", "tax"
        ],
        "Operations": [
            "workflow", "production", "process",
            "delivery", "operations"
        ],
        "Legal & Compliance": [
            "compliance", "contract", "regulation",
            "legal", "agreement"
        ]
    }

    affected = []

    for department, terms in keywords.items():

        if any(term in text for term in terms):
            affected.append(department)

    return affected or ["Manual Review Required"]


# ---------------------------------
# SAVE AUDIT HISTORY
# ---------------------------------

def save_audit(activity, filename, risk, result):

    with get_db() as db:

        db.execute("""
            INSERT INTO audit_logs
            (user_id, activity, filename, risk_level,
             risk_score, result)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            activity,
            filename,
            risk["level"],
            risk["score"],
            json.dumps(result)
        ))


# ---------------------------------
# DASHBOARD
# ---------------------------------

@app.route("/")
@login_required
def home():

    return render_template("index.html")


# ---------------------------------
# DOCUMENT ANALYSIS
# ---------------------------------

@app.route("/api/analyze", methods=["POST"])
@login_required
def analyze_document():

    if "document" not in request.files:
        return jsonify({"error": "Document missing."}), 400

    file = request.files["document"]

    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file format."}), 400

    try:

        text = extract_text(file)

        if not text.strip():
            return jsonify({
                "error": "No readable text found."
            }), 400

        risk = assess_risk(text)
        departments = detect_departments(text)

        result = {
            "success": True,
            "filename": secure_filename(file.filename),
            "word_count": len(text.split()),
            "characters": len(text),
            "risk": risk,
            "departments": departments,
            "summary": text[:500]
        }

        save_audit(
            "Document Analysis",
            result["filename"],
            risk,
            result
        )

        return jsonify(result)

    except Exception as error:
        return jsonify({"error": str(error)}), 400


# ---------------------------------
# DOCUMENT COMPARISON
# ---------------------------------


@app.route("/api/compare", methods=["POST"])
@login_required
def compare_documents():

    old_file = request.files.get("old_document")
    new_file = request.files.get("new_document")

    if not old_file or not new_file:
        return jsonify({
            "error": "Both documents are required."
        }), 400

    if not allowed_file(old_file.filename):
        return jsonify({"error": "Invalid old document."}), 400

    if not allowed_file(new_file.filename):
        return jsonify({"error": "Invalid new document."}), 400

    try:
        old_text = extract_text(old_file)
        new_text = extract_text(new_file)

        if not old_text.strip() or not new_text.strip():
            return jsonify({
                "error": "Documents contain no readable text."
            }), 400

        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        matcher = SequenceMatcher(
            None,
            old_lines,
            new_lines,
            autojunk=False
        )

        rows = []
        added_count = 0
        removed_count = 0
        unchanged_count = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():

            if tag == "equal":

                for offset in range(i2 - i1):
                    rows.append({
                        "old_line": i1 + offset + 1,
                        "old_text": old_lines[i1 + offset],
                        "old_status": "unchanged",

                        "new_line": j1 + offset + 1,
                        "new_text": new_lines[j1 + offset],
                        "new_status": "unchanged"
                    })

                    unchanged_count += 1

            elif tag == "replace":

                old_count = i2 - i1
                new_count = j2 - j1
                max_count = max(old_count, new_count)

                for offset in range(max_count):

                    has_old = offset < old_count
                    has_new = offset < new_count

                    rows.append({
                        "old_line": (
                            i1 + offset + 1 if has_old else None
                        ),
                        "old_text": (
                            old_lines[i1 + offset] if has_old else ""
                        ),
                        "old_status": (
                            "removed" if has_old else "empty"
                        ),

                        "new_line": (
                            j1 + offset + 1 if has_new else None
                        ),
                        "new_text": (
                            new_lines[j1 + offset] if has_new else ""
                        ),
                        "new_status": (
                            "added" if has_new else "empty"
                        )
                    })

                    if has_old:
                        removed_count += 1

                    if has_new:
                        added_count += 1

            elif tag == "delete":

                for i in range(i1, i2):

                    rows.append({
                        "old_line": i + 1,
                        "old_text": old_lines[i],
                        "old_status": "removed",

                        "new_line": None,
                        "new_text": "",
                        "new_status": "empty"
                    })

                    removed_count += 1

            elif tag == "insert":

                for j in range(j1, j2):

                    rows.append({
                        "old_line": None,
                        "old_text": "",
                        "old_status": "empty",

                        "new_line": j + 1,
                        "new_text": new_lines[j],
                        "new_status": "added"
                    })

                    added_count += 1

        risk = assess_risk(
            " ".join(
                [r["old_text"] for r in rows] +
                [r["new_text"] for r in rows]
            )
        )

        departments = detect_departments(
            " ".join(
                [r["old_text"] for r in rows] +
                [r["new_text"] for r in rows]
            )
        )

        result = {
            "success": True,
            "similarity": round(
                SequenceMatcher(
                    None, old_text, new_text
                ).ratio() * 100, 2
            ),
            "added_count": added_count,
            "removed_count": removed_count,
            "unchanged_count": unchanged_count,
            "total_changes": added_count + removed_count,
            "rows": rows,
            "risk": risk,
            "departments": departments
        }

        save_audit(
            "Document Comparison",
            secure_filename(new_file.filename),
            risk,
            result
        )

        return jsonify(result)

    except Exception:
        app.logger.exception("Document comparison failed")

        return jsonify({
            "error": "Comparison failed. Please check your files."
        }), 500



# ---------------------------------
# AUDIT HISTORY API
# ---------------------------------

@app.route("/api/history")
@login_required
def history():

    with get_db() as db:

        logs = db.execute("""
            SELECT id, activity, filename, risk_level,
                   risk_score, created_at
            FROM audit_logs
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 100
        """, (session["user_id"],)).fetchall()

    return jsonify({
        "success": True,
        "history": [dict(row) for row in logs]
    })


# ---------------------------------
# ERROR HANDLERS
# ---------------------------------

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "error": "Maximum file size is 10 MB."
    }), 413
    
# ---------------------------------
# ADVANCED AI IMPACT AUDIT API
# ---------------------------------

@app.route("/api/ai-impact", methods=["POST"])
@login_required
def ai_impact_audit():

    old_file = request.files.get("old_document")
    new_file = request.files.get("new_document")

    if not old_file or not new_file:
        return jsonify({
            "error": "Please upload both old and new documents."
        }), 400

    if not allowed_file(old_file.filename):
        return jsonify({"error": "Invalid old document format."}), 400

    if not allowed_file(new_file.filename):
        return jsonify({"error": "Invalid new document format."}), 400

    try:

        old_text = extract_text(old_file)
        new_text = extract_text(new_file)

        if not old_text.strip() or not new_text.strip():
            return jsonify({
                "error": "No readable text found in documents."
            }), 400

        result = analyze_impact(old_text, new_text)

        result["old_filename"] = secure_filename(old_file.filename)
        result["new_filename"] = secure_filename(new_file.filename)

        save_audit(
            "Advanced AI Impact Analysis",
            result["new_filename"],
            result["risk"],
            result
        )

        return jsonify(result)

    except Exception as error:

        app.logger.exception("AI impact analysis failed")

        return jsonify({
            "error": "Analysis failed. Please check the documents."
        }), 500



if __name__ == "__main__":

    app.run(debug=True)