from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3, os, csv, io

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "exam_management.db")
IST = ZoneInfo("Asia/Kolkata")

app = Flask(__name__)
app.secret_key = os.environ.get("EMS_SECRET_KEY", "change-this-secret-key-before-deployment")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS exams(
      id INTEGER PRIMARY KEY AUTOINCREMENT, exam_type TEXT NOT NULL DEFAULT 'Theory',
      title TEXT NOT NULL, subject_code TEXT NOT NULL, subject_name TEXT NOT NULL,
      branch TEXT NOT NULL, semester TEXT NOT NULL, exam_date TEXT NOT NULL,
      start_time TEXT NOT NULL, end_time TEXT NOT NULL, notes TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS student_batches(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      exam_id INTEGER NOT NULL,
      branch TEXT NOT NULL,
      semester TEXT NOT NULL,
      from_usn TEXT NOT NULL,
      to_usn TEXT NOT NULL,
      FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS rooms(
      id INTEGER PRIMARY KEY AUTOINCREMENT, room_no TEXT UNIQUE NOT NULL,
      block TEXT NOT NULL, capacity INTEGER NOT NULL CHECK(capacity > 0),
      notes TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS staff(
      id INTEGER PRIMARY KEY AUTOINCREMENT, staff_code TEXT UNIQUE NOT NULL,
      staff_name TEXT NOT NULL, designation TEXT DEFAULT '',
      department TEXT NOT NULL, phone TEXT DEFAULT '', email TEXT DEFAULT '',
      active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS allotments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      exam_id INTEGER NOT NULL,
      room_id INTEGER NOT NULL,
      branch TEXT NOT NULL,
      semester TEXT NOT NULL,
      from_usn TEXT NOT NULL,
      to_usn TEXT NOT NULL,
      student_count INTEGER NOT NULL,
      FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE,
      FOREIGN KEY(room_id) REFERENCES rooms(id)
    );
    CREATE TABLE IF NOT EXISTS staff_duties(
      id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER NOT NULL,
      staff_id INTEGER NOT NULL, duty_role TEXT NOT NULL, room_id INTEGER,
      FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE,
      FOREIGN KEY(staff_id) REFERENCES staff(id),
      FOREIGN KEY(room_id) REFERENCES rooms(id)
    );
    """)
    user = con.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not user:
        con.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",
                    ("admin", generate_password_hash("Admin@123")))
    con.commit()
    con.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def now_ist():
    return datetime.now(IST).strftime("%d-%m-%Y %I:%M %p IST")

import re

def parse_usn(usn):
    usn = usn.strip().upper()
    match = re.fullmatch(r"(.+?)(\d+)", usn)

    if not match:
        raise ValueError("Invalid USN format")

    prefix = match.group(1)
    number = int(match.group(2))
    width = len(match.group(2))

    return prefix, number, width

def usn_count(from_usn, to_usn):
    try:
        start_prefix, start_num, _ = parse_usn(from_usn)
        end_prefix, end_num, _ = parse_usn(to_usn)

        if start_prefix != end_prefix or end_num < start_num:
            return 0

        return end_num - start_num + 1

    except (ValueError, TypeError):
        return 0
    
def format_usn(prefix, number, width):
    return prefix + str(number).zfill(width)

def overlap(exam_a, exam_b):
    # Exams overlap only when date is the same and time ranges intersect.
    if exam_a["exam_date"] != exam_b["exam_date"]:
        return False
    return exam_a["start_time"] < exam_b["end_time"] and exam_b["start_time"] < exam_a["end_time"]

@app.context_processor
def common():
    return {
        "now_ist": now_ist,
        "active_endpoint": request.endpoint,
        "usn_count": usn_count
    }
    
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        con = db()
        user = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        con.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    con = db()
    stats = {
        "exams": con.execute("SELECT COUNT(*) FROM exams").fetchone()[0],
        "students": sum(
            parse_usn(row["to_usn"])[1] - parse_usn(row["from_usn"])[1] + 1
            for row in con.execute(
                "SELECT from_usn, to_usn FROM student_batches"
            ).fetchall()
        ),
        "rooms": con.execute("SELECT COUNT(*) FROM rooms WHERE active=1").fetchone()[0],
        "staff": con.execute("SELECT COUNT(*) FROM staff WHERE active=1").fetchone()[0],
    }
    upcoming = con.execute("""SELECT * FROM exams ORDER BY exam_date,start_time LIMIT 5""").fetchall()
    con.close()
    return render_template("dashboard.html", stats=stats, upcoming=upcoming)

@app.route("/exams")
@login_required
def exams():
    con = db()
    rows = con.execute("SELECT * FROM exams ORDER BY exam_date,start_time").fetchall()
    con.close()
    return render_template("exams.html", rows=rows)

@app.route("/exams/add", methods=["GET","POST"])
@app.route("/exams/<int:item_id>/edit", methods=["GET","POST"])
@login_required
def exam_form(item_id=None):
    con = db()
    item = con.execute("SELECT * FROM exams WHERE id=?", (item_id,)).fetchone() if item_id else None
    if item_id and not item:
        con.close(); abort(404)
    if request.method == "POST":
        data = [request.form.get(k,"").strip() for k in
                ("exam_type","title","subject_code","subject_name","branch","semester","exam_date","start_time","end_time","notes")]
        if not all(data[i] for i in range(9)):
            flash("Please complete all required examination fields.", "error")
        elif data[7] >= data[8]:
            flash("End time must be later than start time.", "error")
        else:
            if item_id:
                con.execute("""UPDATE exams SET exam_type=?,title=?,subject_code=?,subject_name=?,branch=?,semester=?,
                    exam_date=?,start_time=?,end_time=?,notes=? WHERE id=?""", (*data,item_id))
                # Clear existing room and staff assignments if the exam schedule is changed.
                con.execute("DELETE FROM allotments WHERE exam_id=?", (item_id,))
            else:
                con.execute("""INSERT INTO exams(exam_type,title,subject_code,subject_name,branch,semester,exam_date,
                    start_time,end_time,notes) VALUES(?,?,?,?,?,?,?,?,?,?)""", data)
            con.commit(); con.close()
            flash("Examination saved successfully.", "success")
            return redirect(url_for("exams"))
    con.close()
    return render_template("exam_form.html", item=item)

@app.route("/exams/<int:item_id>")
@login_required
def exam_view(item_id):
    con=db()
    item=con.execute("SELECT * FROM exams WHERE id=?",(item_id,)).fetchone()
    if not item: con.close(); abort(404)
    batches=con.execute("SELECT * FROM student_batches WHERE exam_id=? ORDER BY branch",(item_id,)).fetchall()
    con.close()
    return render_template("exam_view.html", item=item, batches=batches)

@app.route("/exams/<int:item_id>/delete", methods=["POST"])
@login_required
def exam_delete(item_id):
    con=db(); con.execute("DELETE FROM exams WHERE id=?", (item_id,)); con.commit(); con.close()
    flash("Examination deleted.", "success")
    return redirect(url_for("exams"))

@app.route("/students")
@login_required
def students():
    con=db()
    rows=con.execute("""SELECT b.*,e.title,e.exam_date,e.subject_code FROM student_batches b
        JOIN exams e ON e.id=b.exam_id ORDER BY e.exam_date,b.branch""").fetchall()
    con.close()
    return render_template("students.html", rows=rows)

@app.route("/students/add", methods=["GET", "POST"])
@app.route("/students/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def student_form(item_id=None):
    con = db()

    item = con.execute(
        "SELECT * FROM student_batches WHERE id=?",
        (item_id,)
    ).fetchone() if item_id else None

    exam_rows = con.execute(
        "SELECT id, title, exam_date FROM exams ORDER BY exam_date"
    ).fetchall()

    if item_id and not item:
        con.close()
        abort(404)

    if request.method == "POST":
        try:
            exam_id = int(request.form.get("exam_id", ""))
            branch = request.form.get("branch", "").strip().upper()
            semester = request.form.get("semester", "").strip()

            start_usn = request.form.get("from_usn", "").strip().upper()
            end_usn = request.form.get("to_usn", "").strip().upper()

            start_prefix, start_number, start_width = parse_usn(start_usn)
            end_prefix, end_number, end_width = parse_usn(end_usn)

            exam = con.execute(
                "SELECT id FROM exams WHERE id=?",
                (exam_id,)
            ).fetchone()

            if not exam:
                raise ValueError()

            if not branch or not semester:
                raise ValueError()

            if start_prefix != end_prefix or start_number > end_number:
                raise ValueError()

            if item_id:
                con.execute("""
                    UPDATE student_batches
                    SET exam_id=?, branch=?, semester=?,
                        from_usn=?, to_usn=?
                    WHERE id=?
                """, (
                    exam_id, branch, semester,
                    start_usn, end_usn, item_id
                ))

                con.execute(
                    "DELETE FROM allotments WHERE exam_id=?",
                    (exam_id,)
                )
            else:
                con.execute("""
                    INSERT INTO student_batches
                    (exam_id, branch, semester, from_usn, to_usn)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    exam_id, branch, semester,
                    start_usn, end_usn
                ))

            con.commit()
            con.close()

            flash("Student USN range saved successfully.", "success")
            return redirect(url_for("students"))

        except (ValueError, KeyError):
            flash(
                "Enter a valid examination, branch, semester and USN range.",
                "error"
            )

    con.close()

    return render_template(
        "student_form.html",
        item=item,
        exams=exam_rows
    )
    
@app.route("/students/<int:item_id>")
@login_required
def student_view(item_id):
    con=db(); item=con.execute("""SELECT b.*,e.title,e.exam_date FROM student_batches b
        JOIN exams e ON e.id=b.exam_id WHERE b.id=?""",(item_id,)).fetchone()
    con.close()
    if not item: abort(404)
    return render_template("student_view.html", item=item)

@app.route("/students/<int:item_id>/delete", methods=["POST"])
@login_required
def student_delete(item_id):
    con=db(); row=con.execute("SELECT exam_id FROM student_batches WHERE id=?",(item_id,)).fetchone()
    con.execute("DELETE FROM student_batches WHERE id=?",(item_id,))
    if row: con.execute("DELETE FROM allotments WHERE exam_id=?",(row["exam_id"],))
    con.commit(); con.close(); flash("USN range deleted.", "success"); return redirect(url_for("students"))

@app.route("/rooms")
@login_required
def rooms():
    con=db(); rows=con.execute("SELECT * FROM rooms ORDER BY block,room_no").fetchall(); con.close()
    return render_template("rooms.html", rows=rows)

@app.route("/rooms/add", methods=["GET","POST"])
@app.route("/rooms/<int:item_id>/edit", methods=["GET","POST"])
@login_required
def room_form(item_id=None):
    con=db(); item=con.execute("SELECT * FROM rooms WHERE id=?",(item_id,)).fetchone() if item_id else None
    if item_id and not item: con.close(); abort(404)
    if request.method=="POST":
        room=request.form.get("room_no","").strip().upper(); block=request.form.get("block","").strip()
        notes=request.form.get("notes","").strip()
        try: cap=int(request.form.get("capacity","0"))
        except ValueError: cap=0
        if not room or not block or cap<1:
            flash("Enter room number, block and a positive capacity.", "error")
        else:
            try:
                if item_id: con.execute("UPDATE rooms SET room_no=?,block=?,capacity=?,notes=? WHERE id=?",(room,block,cap,notes,item_id))
                else: con.execute("INSERT INTO rooms(room_no,block,capacity,notes) VALUES(?,?,?,?)",(room,block,cap,notes))
                con.commit(); con.close(); flash("Room saved.", "success"); return redirect(url_for("rooms"))
            except sqlite3.IntegrityError:
                flash("That room number already exists.", "error")
    con.close(); return render_template("room_form.html", item=item)

@app.route("/rooms/<int:item_id>")
@login_required
def room_view(item_id):
    con=db(); item=con.execute("SELECT * FROM rooms WHERE id=?",(item_id,)).fetchone(); con.close()
    if not item: abort(404)
    return render_template("room_view.html", item=item)

@app.route("/rooms/<int:item_id>/delete", methods=["POST"])
@login_required
def room_delete(item_id):
    con=db()
    used=con.execute("SELECT COUNT(*) FROM allotments WHERE room_id=?",(item_id,)).fetchone()[0]
    if used:
        con.execute("UPDATE rooms SET active=0 WHERE id=?",(item_id,))
        flash("Room is used in allotment history, so it was deactivated instead of deleted.", "success")
    else:
        con.execute("DELETE FROM rooms WHERE id=?",(item_id,)); flash("Room deleted.", "success")
    con.commit(); con.close(); return redirect(url_for("rooms"))


@app.route("/staff")
@login_required
def staff():
    con = db()
    rows = con.execute(
        "SELECT * FROM staff ORDER BY staff_name"
    ).fetchall()
    con.close()

    return render_template("staff.html", rows=rows)


@app.route("/staff/add", methods=["GET", "POST"])
@app.route("/staff/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def staff_form(item_id=None):
    con = db()

    item = None
    if item_id:
        item = con.execute(
            "SELECT * FROM staff WHERE id=?", (item_id,)
        ).fetchone()

        if not item:
            con.close()
            abort(404)

    if request.method == "POST":
        staff_code = request.form.get("staff_code", "").strip().upper()
        staff_name = request.form.get("staff_name", "").strip()
        designation = request.form.get("designation", "").strip()
        department = request.form.get("department", "").strip()

        if not staff_code or not staff_name or not department:
            flash("Staff ID, name and department are required.", "error")
        else:
            try:
                if item_id:
                    con.execute("""
                        UPDATE staff
                        SET staff_code=?,
                            staff_name=?,
                            designation=?,
                            department=?
                        WHERE id=?
                    """, (
                        staff_code, staff_name,
                        designation, department, item_id
                    ))
                else:
                    con.execute("""
                        INSERT INTO staff
                        (staff_code, staff_name, designation, department)
                        VALUES (?, ?, ?, ?)
                    """, (
                        staff_code, staff_name,
                        designation, department
                    ))

                con.commit()
                con.close()
                flash("Staff details saved successfully.", "success")
                return redirect(url_for("staff"))

            except sqlite3.IntegrityError:
                flash("Staff ID already exists.", "error")

    con.close()
    return render_template("staff_form.html", item=item)


@app.route("/staff/<int:item_id>")
@login_required
def staff_view(item_id):
    con = db()

    item = con.execute(
        "SELECT * FROM staff WHERE id=?", (item_id,)
    ).fetchone()

    duties = con.execute("""
        SELECT d.*, e.title, e.exam_date, e.start_time,
               e.end_time, r.room_no
        FROM staff_duties d
        JOIN exams e ON e.id = d.exam_id
        LEFT JOIN rooms r ON r.id = d.room_id
        WHERE d.staff_id=?
        ORDER BY e.exam_date
    """, (item_id,)).fetchall()

    con.close()

    if not item:
        abort(404)

    return render_template(
        "staff_view.html",
        item=item,
        duties=duties
    )


@app.route("/staff/<int:item_id>/delete", methods=["POST"])
@login_required
def staff_delete(item_id):
    con = db()

    used = con.execute(
        "SELECT COUNT(*) FROM staff_duties WHERE staff_id=?",
        (item_id,)
    ).fetchone()[0]

    if used:
        con.execute(
            "UPDATE staff SET active=0 WHERE id=?",
            (item_id,)
        )
        flash(
            "Staff member has duty history, so the record was deactivated.",
            "success"
        )
    else:
        con.execute(
            "DELETE FROM staff WHERE id=?",
            (item_id,)
        )
        flash("Staff member deleted.", "success")

    con.commit()
    con.close()

    return redirect(url_for("staff"))


@app.route("/resource-optimization", methods=["GET","POST"])
@login_required
def resource_optimization():
    con=db()
    exam_rows=con.execute("SELECT * FROM exams ORDER BY exam_date,start_time").fetchall()
    result=[]
    if request.method=="POST":
        exam_id=int(request.form.get("exam_id","0"))
        exam=con.execute("SELECT * FROM exams WHERE id=?",(exam_id,)).fetchone()
        if not exam:
            flash("Select a valid examination.", "error")
        else:
            batches=con.execute("SELECT * FROM student_batches WHERE exam_id=? ORDER BY branch,from_usn",(exam_id,)).fetchall()
            rooms=con.execute("SELECT * FROM rooms WHERE active=1 ORDER BY capacity,room_no").fetchall()
            con.execute("DELETE FROM allotments WHERE exam_id=?",(exam_id,))
            occupied=con.execute("""SELECT DISTINCT a.room_id FROM allotments a JOIN exams e ON e.id=a.exam_id
                WHERE e.exam_date=? AND e.start_time < ? AND ? < e.end_time""",
                (exam["exam_date"],exam["end_time"],exam["start_time"])).fetchall()
            occupied_ids={r["room_id"] for r in occupied}
            free_rooms=[r for r in rooms if r["id"] not in occupied_ids]
            if not batches: flash("No USN ranges are registered for this examination.", "error")
            elif not free_rooms: flash("No rooms are available for this examination time.", "error")
            else:
                room_index=0
                failed=False
                for batch in batches:
                    prefix, current, width = parse_usn(batch["from_usn"])
                    end_prefix, end, end_width = parse_usn(batch["to_usn"])

                    if prefix != end_prefix:
                        failed = True
                        break
                    while current<=end:
                        while room_index<len(free_rooms) and free_rooms[room_index]["capacity"]<=0:
                            room_index+=1
                        if room_index>=len(free_rooms):
                            failed=True; break
                        room=free_rooms[room_index]
                        count=min(room["capacity"],end-current+1)
                        last = current + count - 1

                        first_usn = format_usn(prefix, current, width)
                        last_usn = format_usn(prefix, last, width)
                        con.execute("""INSERT INTO allotments(exam_id,room_id,branch,semester,from_usn,to_usn,student_count)
                            VALUES(?,?,?,?,?,?,?)""",(exam_id,room["id"],batch["branch"],batch["semester"],first_usn,last_usn,count))
                        # A room may host multiple branches for the same exam if space remains.
                        free_rooms[room_index]=dict(room)
                        free_rooms[room_index]["capacity"]-=count
                        if free_rooms[room_index]["capacity"]<=0: room_index+=1
                        current=last+1
                    if failed: break
                if failed:
                    con.execute("DELETE FROM allotments WHERE exam_id=?",(exam_id,))
                    flash("Insufficient available room capacity. Add rooms or reduce the registered USN ranges.", "error")
                else:
                    con.commit(); flash("Room allotment generated successfully.", "success")
            con.commit()
    result=con.execute("""SELECT a.*,r.room_no,r.block,e.title,e.exam_date,e.start_time,e.end_time
        FROM allotments a JOIN rooms r ON r.id=a.room_id JOIN exams e ON e.id=a.exam_id
        ORDER BY e.exam_date,r.room_no,a.branch""").fetchall()
    con.close()
    return render_template("resource.html", exams=exam_rows, rows=result)

@app.route("/allotment")
@login_required
def allotment():
    con=db(); rows=con.execute("""SELECT a.*,r.room_no,r.block,e.title,e.exam_date,e.start_time,e.end_time
        FROM allotments a JOIN rooms r ON r.id=a.room_id JOIN exams e ON e.id=a.exam_id
        ORDER BY e.exam_date,r.room_no,a.branch""").fetchall(); con.close()
    return render_template("allotment.html", rows=rows)

@app.route("/allotment/<int:item_id>/delete", methods=["POST"])
@login_required
def allotment_delete(item_id):
    con=db(); con.execute("DELETE FROM allotments WHERE id=?",(item_id,)); con.commit(); con.close()
    flash("Allotment entry deleted.", "success"); return redirect(url_for("allotment"))

@app.route("/staff-duty", methods=["GET","POST"])
@login_required
def staff_duty():
    con=db()
    if request.method=="POST":
        try:
            exam_id=int(request.form["exam_id"]); staff_id=int(request.form["staff_id"])
            room_id=request.form.get("room_id") or None
            room_id=int(room_id) if room_id else None
            role=request.form.get("duty_role","Invigilator").strip()
            target=con.execute("SELECT * FROM exams WHERE id=?",(exam_id,)).fetchone()
            person=con.execute("SELECT * FROM staff WHERE id=? AND active=1",(staff_id,)).fetchone()
            if not target or not person: raise ValueError()
            existing=con.execute("""SELECT e.* FROM staff_duties d JOIN exams e ON e.id=d.exam_id
                WHERE d.staff_id=?""",(staff_id,)).fetchall()
            clash=any(overlap(target, other) for other in existing)
            duplicate=con.execute("SELECT COUNT(*) FROM staff_duties WHERE exam_id=? AND staff_id=?",(exam_id,staff_id)).fetchone()[0]
            if clash: flash("Duty conflict: this staff member already has an examination during that time.", "error")
            elif duplicate: flash("This staff member is already assigned to this examination.", "error")
            else:
                con.execute("INSERT INTO staff_duties(exam_id,staff_id,duty_role,room_id) VALUES(?,?,?,?)",
                            (exam_id,staff_id,role,room_id))
                con.commit(); flash("Staff duty assigned successfully.", "success")
        except (ValueError,KeyError):
            flash("Please select a valid examination and staff member.", "error")
    exams_rows=con.execute("SELECT * FROM exams ORDER BY exam_date,start_time").fetchall()
    staff_rows=con.execute("SELECT * FROM staff WHERE active=1 ORDER BY staff_name").fetchall()
    room_rows=con.execute("SELECT * FROM rooms WHERE active=1 ORDER BY room_no").fetchall()
    duties=con.execute("""SELECT d.*,s.staff_code,s.staff_name,e.title,e.exam_date,e.start_time,e.end_time,r.room_no
        FROM staff_duties d JOIN staff s ON s.id=d.staff_id JOIN exams e ON e.id=d.exam_id
        LEFT JOIN rooms r ON r.id=d.room_id ORDER BY e.exam_date,e.start_time""").fetchall()
    con.close(); return render_template("staff_duty.html", exams=exams_rows, staff=staff_rows, rooms=room_rows, rows=duties)

@app.route("/staff-duty/<int:item_id>/delete", methods=["POST"])
@login_required
def staff_duty_delete(item_id):
    con=db(); con.execute("DELETE FROM staff_duties WHERE id=?",(item_id,)); con.commit(); con.close()
    flash("Staff duty removed.", "success"); return redirect(url_for("staff_duty"))

@app.route("/practical")
@login_required
def practical():
    con=db(); rows=con.execute("SELECT * FROM exams WHERE exam_type='Practical' ORDER BY exam_date,start_time").fetchall(); con.close()
    return render_template("practical.html", rows=rows)

@app.route("/reports")
@login_required
def reports():
    con=db()
    exams_rows=con.execute("SELECT * FROM exams ORDER BY exam_date,start_time").fetchall()
    allotments=con.execute("""SELECT a.*,r.room_no,e.title,e.exam_date,e.start_time,e.end_time
        FROM allotments a JOIN rooms r ON r.id=a.room_id JOIN exams e ON e.id=a.exam_id
        ORDER BY e.exam_date,r.room_no""").fetchall()
    duties=con.execute("""SELECT s.staff_code,s.staff_name,d.duty_role,e.title,e.exam_date,e.start_time,e.end_time,r.room_no
        FROM staff_duties d JOIN staff s ON s.id=d.staff_id JOIN exams e ON e.id=d.exam_id
        LEFT JOIN rooms r ON r.id=d.room_id ORDER BY e.exam_date,s.staff_name""").fetchall()
    con.close(); return render_template("reports.html", exams=exams_rows, allotments=allotments, duties=duties)

@app.route("/reports/export/<kind>")
@login_required
def export_report(kind):
    con=db()
    if kind=="exams":
        rows=con.execute("SELECT exam_type,title,subject_code,subject_name,branch,semester,exam_date,start_time,end_time FROM exams ORDER BY exam_date").fetchall()
        headers=["Type","Title","Subject Code","Subject Name","Branch","Semester","Date","Start","End"]
    elif kind=="allotments":
        rows=con.execute("""SELECT e.title,e.exam_date,e.start_time,e.end_time,r.room_no,a.branch,a.semester,a.from_usn,a.to_usn,a.student_count
            FROM allotments a JOIN exams e ON e.id=a.exam_id JOIN rooms r ON r.id=a.room_id ORDER BY e.exam_date,r.room_no""").fetchall()
        headers=["Exam","Date","Start","End","Room","Branch","Semester","From USN","To USN","Count"]
    elif kind=="duties":
        rows=con.execute("""SELECT s.staff_code,s.staff_name,d.duty_role,e.title,e.exam_date,e.start_time,e.end_time,r.room_no
            FROM staff_duties d JOIN staff s ON s.id=d.staff_id JOIN exams e ON e.id=d.exam_id LEFT JOIN rooms r ON r.id=d.room_id""").fetchall()
        headers=["Staff ID","Staff Name","Role","Exam","Date","Start","End","Room"]
    else:
        con.close(); abort(404)
    con.close()
    out=io.StringIO(); writer=csv.writer(out); writer.writerow(headers)
    for row in rows: writer.writerow(list(row))
    response=make_response("\ufeff"+out.getvalue())
    response.headers["Content-Type"]="text/csv; charset=utf-8"
    response.headers["Content-Disposition"]=f"attachment; filename={kind}_report.csv"
    return response

@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    if request.method=="POST":
        old=request.form.get("old_password",""); new=request.form.get("new_password","")
        con=db(); user=con.execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone()
        if not check_password_hash(user["password_hash"],old):
            flash("Current password is incorrect.", "error")
        elif len(new)<8:
            flash("New password must contain at least 8 characters.", "error")
        else:
            con.execute("UPDATE users SET password_hash=? WHERE id=?",(generate_password_hash(new),session["user_id"]))
            con.commit(); flash("Password changed successfully.", "success")
        con.close()
    return render_template("settings.html")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
