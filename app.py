
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")


# ---------------- DATABASE CONNECTION ----------------

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "exam_management")
    )


# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM admins WHERE username = %s",
            (username,)
        )

        admin = cursor.fetchone()

        cursor.close()
        db.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin"] = admin["username"]
            return redirect(url_for("dashboard"))

        flash("Invalid username or password!")

    return render_template("login.html")


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    students = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM staff")
    staff = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM rooms")
    rooms = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM exams")
    exams = cursor.fetchone()["total"]

    cursor.close()
    db.close()

    return render_template(
        "dashboard.html",
        students=students,
        staff=staff,
        rooms=rooms,
        exams=exams
    )


# ---------------- EXAMINATION DASHBOARD ----------------

@app.route("/exam-dashboard")
def exam_dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))

    return render_template("exam_dashboard.html")


# ---------------- STUDENT MANAGEMENT ----------------

@app.route("/students", methods=["GET", "POST"])
def students():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        roll_no = request.form["roll_no"]
        course = request.form["course"]
        semester = request.form["semester"]

        cursor.execute(
            """INSERT INTO students
            (roll_no, course, semester)
            VALUES (%s, %s, %s)""",
            (name, roll_no, course, semester)
        )

        db.commit()
        flash("Student added successfully!")

    cursor.execute("SELECT * FROM students ORDER BY id DESC")
    student_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("students.html", students=student_list)


# ---------------- VIEW STUDENT ----------------

@app.route("/student/view/<int:student_id>")
def view_student(student_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM students WHERE id = %s",
        (student_id,)
    )
    student = cursor.fetchone()

    cursor.close()
    db.close()

    if not student:
        flash("Student not found!")
        return redirect(url_for("students"))

    return render_template("view_student.html", student=student)


# ---------------- EDIT STUDENT ----------------

@app.route("/student/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        roll_no = request.form["roll_no"]
        course = request.form["course"]
        semester = request.form["semester"]

        cursor.execute("""
            UPDATE students
            roll_no = %s, course = %s, semester = %s
            WHERE id = %s
        """, (roll_no, course, semester, student_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Student updated successfully!")
        return redirect(url_for("students"))

    cursor.execute(
        "SELECT * FROM students WHERE id = %s",
        (student_id,)
    )
    student = cursor.fetchone()

    cursor.close()
    db.close()

    if not student:
        flash("Student not found!")
        return redirect(url_for("students"))

    return render_template("edit_student.html", student=student)


# ---------------- DELETE STUDENT ----------------

@app.route("/student/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()

    # Remove the student's seating records first
    cursor.execute(
        "DELETE FROM seat_assignments WHERE student_id = %s",
        (student_id,)
    )

    # Then remove the student
    cursor.execute(
        "DELETE FROM students WHERE id = %s",
        (student_id,)
    )

    db.commit()

    cursor.close()
    db.close()

    flash("Student deleted successfully!")
    return redirect(url_for("students"))


# ---------------- STAFF MANAGEMENT ----------------

@app.route("/staff", methods=["GET", "POST"])
def staff():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        department = request.form["department"]

        cursor.execute(
            "INSERT INTO staff (name, department) VALUES (%s, %s)",
            (name, department)
        )

        db.commit()
        flash("Staff added successfully!")

    cursor.execute("SELECT * FROM staff ORDER BY id DESC")
    staff_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("staff.html", staff=staff_list)


# ---------------- VIEW STAFF ----------------
@app.route("/staff/view/<int:staff_id>")
def view_staff(staff_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM staff WHERE id = %s", (staff_id,)
    )
    member = cursor.fetchone()

    cursor.close()
    db.close()

    if not member:
        flash("Staff not found!")
        return redirect(url_for("staff"))

    return render_template("view_staff.html", member=member)


# ---------------- EDIT STAFF ----------------
@app.route("/staff/edit/<int:staff_id>", methods=["GET", "POST"])
def edit_staff(staff_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        department = request.form["department"]

        cursor.execute("""
            UPDATE staff
            SET name = %s, department = %s
            WHERE id = %s
        """, (name, department, staff_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Staff updated successfully!")
        return redirect(url_for("staff"))

    cursor.execute(
        "SELECT * FROM staff WHERE id = %s", (staff_id,)
    )
    member = cursor.fetchone()

    cursor.close()
    db.close()

    if not member:
        flash("Staff not found!")
        return redirect(url_for("staff"))

    return render_template("edit_staff.html", member=member)


# ---------------- DELETE STAFF ----------------
@app.route("/staff/delete/<int:staff_id>", methods=["POST"])
def delete_staff(staff_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM staff WHERE id = %s", (staff_id,)
    )

    db.commit()
    cursor.close()
    db.close()

    flash("Staff deleted successfully!")
    return redirect(url_for("staff"))


# ---------------- ROOM MANAGEMENT ----------------

@app.route("/rooms", methods=["GET", "POST"])
def rooms():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        room_name = request.form["room_name"]
        capacity = request.form["capacity"]

        cursor.execute(
            "INSERT INTO rooms (room_name, capacity) VALUES (%s, %s)",
            (room_name, capacity)
        )

        db.commit()
        flash("Room added successfully!")

    cursor.execute("SELECT * FROM rooms ORDER BY id DESC")
    room_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("rooms.html", rooms=room_list)


# ---------------- VIEW ROOM ----------------
@app.route("/room/view/<int:room_id>")
def view_room(room_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
    room = cursor.fetchone()

    cursor.close()
    db.close()

    if not room:
        flash("Room not found!")
        return redirect(url_for("rooms"))

    return render_template("view_room.html", room=room)


# ---------------- EDIT ROOM ----------------
@app.route("/room/edit/<int:room_id>", methods=["GET", "POST"])
def edit_room(room_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        room_name = request.form["room_name"]
        capacity = request.form["capacity"]

        cursor.execute("""
            UPDATE rooms
            SET room_name = %s, capacity = %s
            WHERE id = %s
        """, (room_name, capacity, room_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Room updated successfully!")
        return redirect(url_for("rooms"))

    cursor.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
    room = cursor.fetchone()

    cursor.close()
    db.close()

    if not room:
        flash("Room not found!")
        return redirect(url_for("rooms"))

    return render_template("edit_room.html", room=room)


# ---------------- DELETE ROOM ----------------
@app.route("/room/delete/<int:room_id>", methods=["POST"])
def delete_room(room_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
    db.commit()

    cursor.close()
    db.close()

    flash("Room deleted successfully!")
    return redirect(url_for("rooms"))


# ---------------- SUBJECT MANAGEMENT ----------------

@app.route("/subjects", methods=["GET", "POST"])
def subjects():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        subject_name = request.form["subject_name"]
        subject_code = request.form["subject_code"]

        cursor.execute(
            """INSERT INTO subjects (subject_name, subject_code)
            VALUES (%s, %s)""",
            (subject_name, subject_code)
        )

        db.commit()
        flash("Subject added successfully!")

    cursor.execute("SELECT * FROM subjects ORDER BY id DESC")
    subject_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("subjects.html", subjects=subject_list)


# ---------------- VIEW SUBJECT ----------------
@app.route("/subject/view/<int:subject_id>")
def view_subject(subject_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM subjects WHERE id = %s", (subject_id,)
    )
    subject = cursor.fetchone()

    cursor.close()
    db.close()

    if not subject:
        flash("Subject not found!")
        return redirect(url_for("subjects"))

    return render_template("view_subject.html", subject=subject)


# ---------------- EDIT SUBJECT ----------------
@app.route("/subject/edit/<int:subject_id>", methods=["GET", "POST"])
def edit_subject(subject_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        subject_name = request.form["subject_name"]
        subject_code = request.form["subject_code"]

        cursor.execute("""
            UPDATE subjects
            SET subject_name = %s, subject_code = %s
            WHERE id = %s
        """, (subject_name, subject_code, subject_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Subject updated successfully!")
        return redirect(url_for("subjects"))

    cursor.execute(
        "SELECT * FROM subjects WHERE id = %s", (subject_id,)
    )
    subject = cursor.fetchone()

    cursor.close()
    db.close()

    if not subject:
        flash("Subject not found!")
        return redirect(url_for("subjects"))

    return render_template("edit_subject.html", subject=subject)


# ---------------- DELETE SUBJECT ----------------
@app.route("/subject/delete/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM subjects WHERE id = %s", (subject_id,)
    )

    db.commit()
    cursor.close()
    db.close()

    flash("Subject deleted successfully!")
    return redirect(url_for("subjects"))


# ---------------- EXAM TIMETABLE ----------------

@app.route("/exams", methods=["GET", "POST"])
def exams():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        subject_id = request.form["subject_id"]
        exam_date = request.form["exam_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        course = request.form["course"]
        semester = request.form["semester"]

        cursor.execute(
            """INSERT INTO exams
            (subject_id, exam_date, start_time, end_time, course, semester)
            VALUES (%s, %s, %s, %s, %s, %s)""",
            (subject_id, exam_date, start_time, end_time, course, semester)
        )

        db.commit()
        flash("Exam scheduled successfully!")

    cursor.execute("""
        SELECT exams.*, subjects.subject_name
        FROM exams
        JOIN subjects ON exams.subject_id = subjects.id
        ORDER BY exams.exam_date, exams.start_time
    """)
    exam_list = cursor.fetchall()

    cursor.execute("SELECT * FROM subjects ORDER BY subject_name")
    subject_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "exams.html",
        exams=exam_list,
        subjects=subject_list
    )


# ---------------- ROOM ALLOCATION ----------------

@app.route("/allocations", methods=["GET", "POST"])
def allocations():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        exam_id = request.form["exam_id"]
        room_id = request.form["room_id"]

        cursor.execute(
            "SELECT * FROM allocations WHERE exam_id = %s",
            (exam_id,)
        )
        existing = cursor.fetchone()

        cursor.execute(
            "SELECT course, semester FROM exams WHERE id = %s",
            (exam_id,)
        )
        exam = cursor.fetchone()

        cursor.execute(
            """SELECT COUNT(*) AS total FROM students
            WHERE course = %s AND semester = %s""",
            (exam["course"], exam["semester"])
        )
        student_count = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT * FROM rooms WHERE id = %s",
            (room_id,)
        )
        room = cursor.fetchone()

        if existing:
            flash("Room already allocated for this exam!")
        elif not student_count:
            flash("No students found for this exam!")
        elif room and room["capacity"] >= student_count:
            cursor.execute(
                """INSERT INTO allocations (exam_id, room_id)
                VALUES (%s, %s)""",
                (exam_id, room_id)
            )
            db.commit()
            flash("Room allocated successfully!")
        else:
            flash("Room capacity is insufficient!")

    cursor.execute("""
    SELECT a.id AS allocation_id, a.exam_id,s.subject_name,e.exam_date,r.room_name,r.capacity
        FROM allocations a
        JOIN exams e ON a.exam_id = e.id
        JOIN subjects s ON e.subject_id = s.id
        JOIN rooms r ON a.room_id = r.id
        ORDER BY e.exam_date
    """)
    allocation_list = cursor.fetchall()

    cursor.execute("""
        SELECT e.id, s.subject_name, e.exam_date, e.course, e.semester
        FROM exams e
        JOIN subjects s ON e.subject_id = s.id
        ORDER BY e.exam_date
    """)
    exam_list = cursor.fetchall()

    cursor.execute("SELECT * FROM rooms ORDER BY room_name")
    room_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "allocations.html",
        allocations=allocation_list,
        exams=exam_list,
        rooms=room_list
    )


# ---------------- STAFF ALLOCATION ----------------

@app.route("/staff-allocation", methods=["GET", "POST"])
def staff_allocation():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        exam_id = request.form["exam_id"]
        staff_id = request.form["staff_id"]

        cursor.execute(
            "SELECT * FROM allocations WHERE exam_id = %s",
            (exam_id,)
        )
        allocation = cursor.fetchone()

        if allocation:
            cursor.execute(
                "UPDATE allocations SET staff_id = %s WHERE exam_id = %s",
                (staff_id, exam_id)
            )
            db.commit()
            flash("Staff allocated successfully!")
        else:
            flash("Please allocate a room for this exam first!")

    cursor.execute("""
        SELECT a.id, e.id AS exam_id, s.subject_name,
               r.room_name, st.name AS staff_name
        FROM allocations a
        JOIN exams e ON a.exam_id = e.id
        JOIN subjects s ON e.subject_id = s.id
        JOIN rooms r ON a.room_id = r.id
        LEFT JOIN staff st ON a.staff_id = st.id
        ORDER BY e.exam_date
    """)
    allocation_list = cursor.fetchall()

    cursor.execute("""
        SELECT e.id, s.subject_name, e.exam_date
        FROM exams e
        JOIN subjects s ON e.subject_id = s.id
        ORDER BY e.exam_date
    """)
    exam_list = cursor.fetchall()

    cursor.execute("SELECT * FROM staff ORDER BY name")
    staff_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "staff_allocation.html",
        allocations=allocation_list,
        exams=exam_list,
        staff=staff_list
    )

# ---------------- AUTOMATIC RESOURCE OPTIMIZATION ----------------


# ---------------- AUTOMATIC RESOURCE OPTIMIZATION ----------------

@app.route("/optimize", methods=["GET", "POST"])
def optimize():

    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Run optimization when button is clicked
        if request.method == "POST":

            cursor.execute("""
                SELECT *
                FROM exams
                ORDER BY exam_date, start_time
            """)

            exam_list = cursor.fetchall()

            allocated_count = 0

            for exam in exam_list:

                # Check whether this exam is already allocated
                cursor.execute("""
                    SELECT id
                    FROM allocations
                    WHERE exam_id = %s
                """, (exam["id"],))

                existing = cursor.fetchone()

                if existing:
                    continue

                # Count students for this exam
                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM students
                    WHERE course = %s
                    AND semester = %s
                """, (exam["course"], exam["semester"]))

                student_count = cursor.fetchone()["total"]

                if student_count <= 0:
                    continue

                # Find a suitable room
                cursor.execute("""
                    SELECT *
                    FROM rooms
                    WHERE capacity >= %s
                    ORDER BY capacity ASC
                """, (student_count,))

                available_rooms = cursor.fetchall()

                room = None

                for candidate in available_rooms:

                    cursor.execute("""
                        SELECT COUNT(*) AS total
                        FROM allocations a
                        JOIN exams e ON a.exam_id = e.id
                        WHERE a.room_id = %s
                        AND e.exam_date = %s
                        AND e.start_time < %s
                        AND e.end_time > %s
                    """, (
                        candidate["id"],
                        exam["exam_date"],
                        exam["end_time"],
                        exam["start_time"]
                    ))

                    if cursor.fetchone()["total"] == 0:
                        room = candidate
                        break

                # Find available staff
                cursor.execute("""
                    SELECT st.*
                    FROM staff st
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM allocations a
                        JOIN exams e ON a.exam_id = e.id
                        WHERE a.staff_id = st.id
                        AND e.exam_date = %s
                        AND e.start_time < %s
                        AND e.end_time > %s
                    )
                    ORDER BY st.id
                    LIMIT 1
                """, (
                    exam["exam_date"],
                    exam["end_time"],
                    exam["start_time"]
                ))

                staff_member = cursor.fetchone()

                # Save allocation
                if room and staff_member:

                    cursor.execute("""
                        INSERT INTO allocations
                        (exam_id, room_id, staff_id)
                        VALUES (%s, %s, %s)
                    """, (
                        exam["id"],
                        room["id"],
                        staff_member["id"]
                    ))

                    allocated_count += 1

            db.commit()

            flash(
                str(allocated_count) +
                " new exam allocations completed!"
            )

        # Fetch ALL allocation results,
        # including allocations created earlier
        cursor.execute("""
            SELECT
                e.id AS exam_id,
                s.subject_name AS subject_name,

                (
                    SELECT COUNT(*)
                    FROM students st
                    WHERE st.course = e.course
                    AND st.semester = e.semester
                ) AS student_count,

                COALESCE(r.room_name, 'Not Available') AS room_name,

                COALESCE(staff.name, 'Not Available') AS staff_name,

                CASE
                    WHEN a.id IS NOT NULL THEN 'Allocated'
                    ELSE 'Could not allocate'
                END AS status

            FROM exams e

            LEFT JOIN subjects s
                ON e.subject_id = s.id

            LEFT JOIN allocations a
                ON e.id = a.exam_id

            LEFT JOIN rooms r
                ON a.room_id = r.id

            LEFT JOIN staff staff
                ON a.staff_id = staff.id

            ORDER BY e.exam_date, e.start_time
        """)

        results = cursor.fetchall()

        return render_template(
            "optimization.html",
            results=results
        )

    except Exception as error:

        db.rollback()

        flash("Optimization Error: " + str(error))

        return render_template(
            "optimization.html",
            results=[]
        )

    finally:

        cursor.close()
        db.close()


# ---------------- SEATING REPORT ----------------

@app.route("/seating", methods=["GET", "POST"])
def seating():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        try:
            exam_id = int(request.form.get("exam_id", 0))
            student_count = int(request.form.get("student_count", 0))

            if exam_id <= 0 or student_count <= 0:
                flash("Select an exam and enter a valid student count!")
            else:
                cursor.execute("""
                    SELECT id, course, semester
                    FROM exams WHERE id = %s
                """, (exam_id,))
                exam = cursor.fetchone()

                if not exam:
                    flash("Exam not found!")
                else:
                    cursor.execute("""
                        SELECT DISTINCT r.id, r.room_name, r.capacity
                        FROM allocations a
                        JOIN rooms r ON a.room_id = r.id
                        WHERE a.exam_id = %s
                        ORDER BY r.id
                    """, (exam_id,))
                    rooms = cursor.fetchall()

                    cursor.execute("""
                        SELECT id, name, roll_no
                        FROM students
                        WHERE course = %s AND semester = %s
                        ORDER BY roll_no
                    """, (exam["course"], exam["semester"]))
                    students = cursor.fetchall()

                    total_capacity = sum(
                        int(room["capacity"]) for room in rooms
                    )

                    if not rooms:
                        flash("Allocate rooms before generating seating!")
                    elif not students:
                        flash("No students found for this exam!")
                    elif student_count > len(students):
                        flash("Only " + str(len(students)) +
                              " students are available!")
                    elif student_count > total_capacity:
                        flash("Room capacity is insufficient!")
                    else:
                        db.start_transaction()

                        cursor.execute("""
                            DELETE FROM seat_assignments
                            WHERE exam_id = %s
                        """, (exam_id,))

                        count = 0

                        for room in rooms:
                            for seat_no in range(
                                1, int(room["capacity"]) + 1
                            ):
                                if count >= student_count:
                                    break

                                student = students[count]

                                cursor.execute("""
                                    INSERT INTO seat_assignments
                                    (exam_id, student_id, room_id, seat_number)
                                    VALUES (%s, %s, %s, %s)
                                """, (
                                    exam_id,
                                    student["id"],
                                    room["id"],
                                    seat_no
                                ))

                                count += 1

                            if count >= student_count:
                                break

                        db.commit()
                        flash(str(count) +
                              " students assigned seats successfully!")

        except ValueError:
            db.rollback()
            flash("Enter valid exam and student details!")

        except Exception as error:
            db.rollback()
            flash("Seating error: " + str(error))

    cursor.execute("""
        SELECT e.id, s.subject_name, e.exam_date,
               e.course, e.semester
        FROM exams e
        JOIN subjects s ON e.subject_id = s.id
        ORDER BY e.exam_date
    """)
    exam_list = cursor.fetchall()

    cursor.execute("""
        SELECT sa.id AS seat_id, sa.exam_id, sa.seat_number,
               st.roll_no, s.subject_name, r.room_name
        FROM seat_assignments sa
        JOIN students st ON sa.student_id = st.id
        JOIN exams e ON sa.exam_id = e.id
        JOIN subjects s ON e.subject_id = s.id
        JOIN rooms r ON sa.room_id = r.id
        ORDER BY sa.exam_id, r.room_name, sa.seat_number
    """)
    seating_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "seating.html",
        exams=exam_list,
        seating=seating_list
    )
    
# ---------------- EXAMINATION REPORTS ----------------

@app.route("/reports")
def reports():
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.*, s.subject_name
        FROM exams e
        JOIN subjects s ON e.subject_id = s.id
        ORDER BY e.exam_date
    """)
    exam_list = cursor.fetchall()

    cursor.execute("""
        SELECT e.id AS exam_id, s.subject_name, e.exam_date,
               r.room_name, st.name AS staff_name
        FROM allocations a
        JOIN exams e ON a.exam_id = e.id
        JOIN subjects s ON e.subject_id = s.id
        JOIN rooms r ON a.room_id = r.id
        LEFT JOIN staff st ON a.staff_id = st.id
        ORDER BY e.exam_date
    """)
    allocation_list = cursor.fetchall()

    cursor.execute("""
        SELECT sa.seat_number, st.name, st.roll_no,
               s.subject_name, r.room_name
        FROM seat_assignments sa
        JOIN students st ON sa.student_id = st.id
        JOIN exams e ON sa.exam_id = e.id
        JOIN subjects s ON e.subject_id = s.id
        JOIN rooms r ON sa.room_id = r.id
        ORDER BY e.exam_date, sa.seat_number
    """)
    seating_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "reports.html",
        exams=exam_list,
        allocations=allocation_list,
        seating=seating_list
    )


# ==================================================
# EXAM VIEW, EDIT AND DELETE
# ==================================================

@app.route("/exam/view/<int:exam_id>")
def view_exam(exam_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.*, s.subject_name
        FROM exams e
        JOIN subjects s ON e.subject_id = s.id
        WHERE e.id = %s
    """, (exam_id,))

    record = cursor.fetchone()
    cursor.close()
    db.close()

    if not record:
        flash("Exam not found!")
        return redirect(url_for("exams"))

    details = [
        ("Exam ID", record["id"]),
        ("Subject", record["subject_name"]),
        ("Date", record["exam_date"]),
        ("Start Time", record["start_time"]),
        ("End Time", record["end_time"]),
        ("Course", record["course"]),
        ("Semester", record["semester"])
    ]

    return render_template(
        "record_view.html",
        title="Exam Details",
        details=details,
        back_url=url_for("exams")
    )


@app.route("/exam/edit/<int:exam_id>", methods=["GET", "POST"])
def edit_exam(exam_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute("""
            UPDATE exams
            SET subject_id=%s, exam_date=%s,
                start_time=%s, end_time=%s,
                course=%s, semester=%s
            WHERE id=%s
        """, (
            request.form["subject_id"],
            request.form["exam_date"],
            request.form["start_time"],
            request.form["end_time"],
            request.form["course"],
            request.form["semester"],
            exam_id
        ))

        db.commit()
        cursor.close()
        db.close()

        flash("Exam updated successfully!")
        return redirect(url_for("exams"))

    cursor.execute("SELECT * FROM exams WHERE id=%s", (exam_id,))
    record = cursor.fetchone()

    cursor.execute("SELECT * FROM subjects ORDER BY subject_name")
    subjects_list = cursor.fetchall()

    cursor.close()
    db.close()

    if not record:
        flash("Exam not found!")
        return redirect(url_for("exams"))

    return render_template(
        "record_edit.html",
        title="Edit Exam",
        kind="exam",
        record=record,
        subjects=subjects_list
    )


@app.route("/exam/delete/<int:exam_id>", methods=["POST"])
def delete_exam(exam_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()

    # Delete dependent seating and allocation records first.
    cursor.execute(
        "DELETE FROM seat_assignments WHERE exam_id=%s",
        (exam_id,)
    )
    cursor.execute(
        "DELETE FROM allocations WHERE exam_id=%s",
        (exam_id,)
    )
    cursor.execute("DELETE FROM exams WHERE id=%s", (exam_id,))

    db.commit()
    cursor.close()
    db.close()

    flash("Exam and its allocation/seating records deleted!")
    return redirect(url_for("exams"))


# ==================================================
# ROOM ALLOCATION VIEW, EDIT AND DELETE
# ==================================================

@app.route("/allocation/view/<int:allocation_id>")
def view_allocation(allocation_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT a.id, e.id AS exam_id, s.subject_name,
               e.exam_date, e.course, e.semester,
               r.room_name, r.capacity
        FROM allocations a
        JOIN exams e ON a.exam_id=e.id
        JOIN subjects s ON e.subject_id=s.id
        JOIN rooms r ON a.room_id=r.id
        WHERE a.id=%s
    """, (allocation_id,))

    record = cursor.fetchone()
    cursor.close()
    db.close()

    if not record:
        flash("Allocation not found!")
        return redirect(url_for("allocations"))

    details = [
        ("Allocation ID", record["id"]),
        ("Exam ID", record["exam_id"]),
        ("Subject", record["subject_name"]),
        ("Exam Date", record["exam_date"]),
        ("Course", record["course"]),
        ("Semester", record["semester"]),
        ("Room", record["room_name"]),
        ("Room Capacity", record["capacity"])
    ]

    return render_template(
        "record_view.html",
        title="Room Allocation Details",
        details=details,
        back_url=url_for("allocations")
    )


@app.route("/allocation/edit/<int:allocation_id>", methods=["GET", "POST"])
def edit_allocation(allocation_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        room_id = request.form["room_id"]

        cursor.execute("""
            SELECT e.course, e.semester
            FROM allocations a
            JOIN exams e ON a.exam_id=e.id
            WHERE a.id=%s
        """, (allocation_id,))
        exam = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM students
            WHERE course=%s AND semester=%s
        """, (exam["course"], exam["semester"]))
        student_count = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT capacity FROM rooms WHERE id=%s",
            (room_id,)
        )
        room = cursor.fetchone()

        if not room or room["capacity"] < student_count:
            cursor.close()
            db.close()
            flash("Room capacity is insufficient!")
            return redirect(url_for(
                "edit_allocation", allocation_id=allocation_id
            ))

        cursor.execute("""
            UPDATE allocations SET room_id=%s WHERE id=%s
        """, (room_id, allocation_id))

        # Keep existing seating in the same room as the allocation.
        cursor.execute("""
            UPDATE seat_assignments
            SET room_id=%s
            WHERE exam_id=(
                SELECT exam_id FROM allocations WHERE id=%s
            )
        """, (room_id, allocation_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Room allocation updated successfully!")
        return redirect(url_for("allocations"))

    cursor.execute(
        "SELECT * FROM allocations WHERE id=%s",
        (allocation_id,)
    )
    record = cursor.fetchone()

    cursor.execute("SELECT * FROM rooms ORDER BY room_name")
    rooms_list = cursor.fetchall()

    cursor.close()
    db.close()

    if not record:
        flash("Allocation not found!")
        return redirect(url_for("allocations"))

    return render_template(
        "record_edit.html",
        title="Edit Room Allocation",
        kind="allocation",
        record=record,
        rooms=rooms_list
    )


@app.route("/allocation/delete/<int:allocation_id>", methods=["POST"])
def delete_allocation(allocation_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "SELECT exam_id FROM allocations WHERE id=%s",
        (allocation_id,)
    )
    result = cursor.fetchone()

    if result:
        exam_id = result[0]

        cursor.execute(
            "DELETE FROM seat_assignments WHERE exam_id=%s",
            (exam_id,)
        )
        cursor.execute(
            "DELETE FROM allocations WHERE id=%s",
            (allocation_id,)
        )

        db.commit()
        flash("Room allocation and its seating records deleted!")
    else:
        flash("Allocation not found!")

    cursor.close()
    db.close()

    return redirect(url_for("allocations"))


# ==================================================
# STAFF ALLOCATION VIEW, EDIT AND DELETE
# ==================================================

@app.route("/staff-allocation/view/<int:allocation_id>")
def view_staff_allocation(allocation_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT a.id, e.id AS exam_id, s.subject_name,
               e.exam_date, r.room_name, st.name AS staff_name
        FROM allocations a
        JOIN exams e ON a.exam_id=e.id
        JOIN subjects s ON e.subject_id=s.id
        JOIN rooms r ON a.room_id=r.id
        LEFT JOIN staff st ON a.staff_id=st.id
        WHERE a.id=%s
    """, (allocation_id,))

    record = cursor.fetchone()
    cursor.close()
    db.close()

    if not record:
        flash("Staff allocation not found!")
        return redirect(url_for("staff_allocation"))

    details = [
        ("Allocation ID", record["id"]),
        ("Exam ID", record["exam_id"]),
        ("Subject", record["subject_name"]),
        ("Exam Date", record["exam_date"]),
        ("Room", record["room_name"]),
        ("Staff", record["staff_name"] or "Not assigned")
    ]

    return render_template(
        "record_view.html",
        title="Staff Allocation Details",
        details=details,
        back_url=url_for("staff_allocation")
    )


@app.route("/staff-allocation/edit/<int:allocation_id>",
           methods=["GET", "POST"])
def edit_staff_allocation(allocation_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        staff_id = request.form.get("staff_id") or None

        cursor.execute("""
            UPDATE allocations SET staff_id=%s WHERE id=%s
        """, (staff_id, allocation_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Staff allocation updated successfully!")
        return redirect(url_for("staff_allocation"))

    cursor.execute(
        "SELECT * FROM allocations WHERE id=%s",
        (allocation_id,)
    )
    record = cursor.fetchone()

    cursor.execute("SELECT * FROM staff ORDER BY name")
    staff_list = cursor.fetchall()

    cursor.close()
    db.close()

    if not record:
        flash("Staff allocation not found!")
        return redirect(url_for("staff_allocation"))

    return render_template(
        "record_edit.html",
        title="Edit Staff Allocation",
        kind="staff_allocation",
        record=record,
        staff=staff_list
    )


@app.route("/staff-allocation/delete/<int:allocation_id>",
           methods=["POST"])
def delete_staff_allocation(allocation_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()

    # Remove only the staff assignment, not the room allocation.
    cursor.execute("""
        UPDATE allocations SET staff_id=NULL WHERE id=%s
    """, (allocation_id,))

    db.commit()
    cursor.close()
    db.close()

    flash("Staff assignment removed successfully!")
    return redirect(url_for("staff_allocation"))


# ==================================================
# STUDENT SEATING VIEW, EDIT AND DELETE
# ==================================================

@app.route("/seat/view/<int:seat_id>")
def view_seat(seat_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT sa.id, sa.exam_id, sa.seat_number,
               st.name, st.roll_no, s.subject_name,
               e.exam_date, r.room_name
        FROM seat_assignments sa
        JOIN students st ON sa.student_id=st.id
        JOIN exams e ON sa.exam_id=e.id
        JOIN subjects s ON e.subject_id=s.id
        JOIN rooms r ON sa.room_id=r.id
        WHERE sa.id=%s
    """, (seat_id,))

    record = cursor.fetchone()
    cursor.close()
    db.close()

    if not record:
        flash("Seat assignment not found!")
        return redirect(url_for("seating"))

    details = [
        ("Seat ID", record["id"]),
        ("Student Name", record["name"]),
        ("Roll Number", record["roll_no"]),
        ("Subject", record["subject_name"]),
        ("Exam Date", record["exam_date"]),
        ("Room", record["room_name"]),
        ("Seat Number", record["seat_number"])
    ]

    return render_template(
        "record_view.html",
        title="Student Seating Details",
        details=details,
        back_url=url_for("seating")
    )


@app.route("/seat/edit/<int:seat_id>", methods=["GET", "POST"])
def edit_seat(seat_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        seat_number = request.form["seat_number"]

        cursor.execute("""
            SELECT sa.exam_id, r.capacity
            FROM seat_assignments sa
            JOIN rooms r ON sa.room_id=r.id
            WHERE sa.id=%s
        """, (seat_id,))
        seat = cursor.fetchone()

        if not seat:
            cursor.close()
            db.close()
            flash("Seat assignment not found!")
            return redirect(url_for("seating"))

        if not seat_number.isdigit() or int(seat_number) < 1:
            cursor.close()
            db.close()
            flash("Enter a valid seat number!")
            return redirect(url_for("edit_seat", seat_id=seat_id))

        if int(seat_number) > seat["capacity"]:
            cursor.close()
            db.close()
            flash("Seat number exceeds room capacity!")
            return redirect(url_for("edit_seat", seat_id=seat_id))

        cursor.execute("""
            SELECT id FROM seat_assignments
            WHERE exam_id=%s AND seat_number=%s AND id<>%s
        """, (seat["exam_id"], seat_number, seat_id))

        if cursor.fetchone():
            cursor.close()
            db.close()
            flash("This seat number is already assigned!")
            return redirect(url_for("edit_seat", seat_id=seat_id))

        cursor.execute("""
            UPDATE seat_assignments
            SET seat_number=%s WHERE id=%s
        """, (seat_number, seat_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Seat number updated successfully!")
        return redirect(url_for("seating"))

    cursor.execute("""
        SELECT sa.*, st.name, st.roll_no, s.subject_name
        FROM seat_assignments sa
        JOIN students st ON sa.student_id=st.id
        JOIN exams e ON sa.exam_id=e.id
        JOIN subjects s ON e.subject_id=s.id
        WHERE sa.id=%s
    """, (seat_id,))

    record = cursor.fetchone()
    cursor.close()
    db.close()

    if not record:
        flash("Seat assignment not found!")
        return redirect(url_for("seating"))

    return render_template(
        "record_edit.html",
        title="Edit Student Seat",
        kind="seat",
        record=record
    )


@app.route("/seat/delete/<int:seat_id>", methods=["POST"])
def delete_seat(seat_id):
    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM seat_assignments WHERE id=%s",
        (seat_id,)
    )

    db.commit()
    cursor.close()
    db.close()

    flash("Seat assignment deleted successfully!")
    return redirect(url_for("seating"))


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- RUN APPLICATION ----------------

if __name__ == '__main__':
    app.run(debug=True)
