from flask import Flask, render_template, request, redirect, url_for
from datetime import date
import sqlite3
import math

app = Flask(__name__)
DB_NAME = "attendance.db"

# ---------- DATABASE ----------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll TEXT NOT NULL,
            status TEXT NOT NULL,
            date TEXT NOT NULL,
            reason TEXT
        )
    """)

    conn.commit()
    conn.close()

create_tables()
# ----------------------------

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    role = request.form.get("role")
    return redirect(
        url_for("admin_dashboard" if role == "admin" else "student_dashboard")
    )

@app.route("/admin")
def admin_dashboard():
    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", students=students)

@app.route("/student")
def student_dashboard():
    return render_template("student_dashboard.html")

@app.route("/add_student", methods=["POST"])
def add_student():
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO students (name, roll) VALUES (?, ?)",
            (request.form.get("name"), request.form.get("roll"))
        )
        conn.commit()
    except:
        pass
    conn.close()
    return redirect(url_for("admin_dashboard"))

# ---------- MARK ATTENDANCE ----------
@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    roll = request.form.get("roll")
    status = request.form.get("status")
    today = date.today().isoformat()

    conn = get_db_connection()

    # 🔒 DUPLICATE ATTENDANCE PREVENTION
    existing = conn.execute(
        "SELECT * FROM attendance WHERE roll = ? AND date = ?",
        (roll, today)
    ).fetchone()

    if existing:
        conn.close()
        print("DUPLICATE BLOCKED: Attendance already marked for roll", roll)
        return redirect(url_for("admin_dashboard"))

    # INSERT ATTENDANCE
    conn.execute(
        "INSERT INTO attendance (roll, status, date) VALUES (?, ?, ?)",
        (roll, status, today)
    )

    # 🔔 PARENT ALERT (SIMULATION)
    if status == "Absent":
        print(
            "ALERT: Parent notified - Student with roll",
            roll,
            "was absent today"
        )

    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))
# -----------------------------------

@app.route("/edit_attendance", methods=["POST"])
def edit_attendance():
    record_id = request.form.get("id")
    current_status = request.form.get("current_status")

    new_status = "Absent" if current_status == "Present" else "Present"

    conn = get_db_connection()
    conn.execute(
        "UPDATE attendance SET status = ? WHERE id = ?",
        (new_status, record_id)
    )

    if new_status == "Present":
        conn.execute(
            "UPDATE attendance SET reason = NULL WHERE id = ?",
            (record_id,)
        )

    conn.commit()
    conn.close()
    return redirect(url_for("attendance_report"))

@app.route("/submit_reason", methods=["POST"])
def submit_reason():
    conn = get_db_connection()
    conn.execute("""
        UPDATE attendance
        SET reason = ?
        WHERE roll = ? AND date = ? AND status = 'Absent'
    """, (
        request.form.get("reason"),
        request.form.get("roll"),
        request.form.get("date")
    ))
    conn.commit()
    conn.close()
    return redirect(url_for("student_dashboard"))

@app.route("/attendance_report")
def attendance_report():
    conn = get_db_connection()
    records = conn.execute("SELECT * FROM attendance").fetchall()
    conn.close()
    return render_template("attendance_report.html", attendance=records)

@app.route("/student_report", methods=["POST"])
def student_report():
    roll = request.form.get("roll")

    conn = get_db_connection()
    records = conn.execute(
        "SELECT * FROM attendance WHERE roll = ?",
        (roll,)
    ).fetchall()
    conn.close()

    total = len(records)
    present = len([r for r in records if r["status"] == "Present"])
    absent = len([r for r in records if r["status"] == "Absent"])

    percentage = (present / total * 100) if total > 0 else 0

    allowed_absent = math.floor(total * 0.25)
    remaining_leaves = max(allowed_absent - absent, 0)

    if percentage >= 75:
        status = "SAFE"
    elif percentage >= 70:
        status = "WARNING"
    else:
        status = "AT RISK"

    return render_template(
        "student_report.html",
        roll=roll,
        records=records,
        total=total,
        present=present,
        absent=absent,
        percentage=round(percentage, 2),
        allowed_absent=allowed_absent,
        remaining_leaves=remaining_leaves,
        status=status
    )

if __name__ == "__main__":
    app.run(debug=True)
