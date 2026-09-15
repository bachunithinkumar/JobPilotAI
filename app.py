from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "jobpilotai-secret-key-change-this"

DATABASE = "jobpilot.db"


# ---------------- DATABASE CONNECTION ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- DATABASE INITIALIZATION ----------------

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            job_type TEXT NOT NULL,
            salary TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Applied',
            applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
    """)

    # Add sample jobs only if database is empty
    job_count = conn.execute(
        "SELECT COUNT(*) FROM jobs"
    ).fetchone()[0]

    if job_count == 0:
        sample_jobs = [
            (
                "Junior Python Developer",
                "TechNova",
                "London",
                "Full-time",
                "£28,000 - £35,000",
                "We are looking for a junior Python developer to join our growing engineering team."
            ),
            (
                "Frontend Developer",
                "BrightWeb",
                "London",
                "Part-time",
                "£15 - £20 per hour",
                "Work with HTML, CSS and JavaScript to create responsive websites."
            ),
            (
                "AI Research Intern",
                "FutureAI Labs",
                "Remote",
                "Internship",
                "£500 per month",
                "Support machine learning experiments and AI research projects."
            ),
            (
                "Software Engineer Graduate",
                "CodeWorks",
                "Manchester",
                "Full-time",
                "£30,000 - £38,000",
                "Graduate opportunity for aspiring software engineers."
            ),
            (
                "Data Entry Assistant",
                "OfficePlus",
                "London",
                "Part-time",
                "£13.50 per hour",
                "Assist the administration team with data entry and document management."
            )
        ]

        conn.executemany("""
            INSERT INTO jobs
            (title, company, location, job_type, salary, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_jobs)

    conn.commit()
    conn.close()


# ---------------- LOGIN REQUIRED DECORATOR ----------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# ---------------- HOME PAGE ----------------

@app.route("/")
def index():
    conn = get_db()

    jobs = conn.execute("""
        SELECT * FROM jobs
        ORDER BY id DESC
        LIMIT 6
    """).fetchall()

    conn.close()

    return render_template("index.html", jobs=jobs)


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:
            conn.execute("""
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
            """, (name, email, hashed_password))

            conn.commit()

            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")

        finally:
            conn.close()

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute("""
            SELECT * FROM users WHERE email = ?
        """, (email,)).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            flash("Login successful!", "success")
            return redirect(url_for("jobs"))

        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("index"))


# ---------------- JOB SEARCH ----------------

@app.route("/jobs")
def jobs():

    search = request.args.get("search", "")
    location = request.args.get("location", "")
    job_type = request.args.get("job_type", "")

    conn = get_db()

    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if search:
        query += " AND (title LIKE ? OR company LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    if job_type:
        query += " AND job_type = ?"
        params.append(job_type)

    query += " ORDER BY id DESC"

    jobs_list = conn.execute(query, params).fetchall()

    conn.close()

    return render_template(
        "jobs.html",
        jobs=jobs_list,
        search=search,
        location=location,
        job_type=job_type
    )


# ---------------- APPLY FOR JOB ----------------

@app.route("/apply/<int:job_id>", methods=["POST"])
@login_required
def apply(job_id):

    user_id = session["user_id"]

    conn = get_db()

    existing_application = conn.execute("""
        SELECT * FROM applications
        WHERE user_id = ? AND job_id = ?
    """, (user_id, job_id)).fetchone()

    if existing_application:

        flash("You have already applied for this job.", "warning")

    else:

        conn.execute("""
            INSERT INTO applications (user_id, job_id)
            VALUES (?, ?)
        """, (user_id, job_id))

        conn.commit()

        flash("Application submitted successfully!", "success")

    conn.close()

    return redirect(url_for("jobs"))


# ---------------- USER DASHBOARD ----------------

@app.route("/dashboard")
@login_required
def dashboard():

    user_id = session["user_id"]

    conn = get_db()

    applications = conn.execute("""
        SELECT
            applications.id,
            applications.status,
            applications.applied_date,
            jobs.title,
            jobs.company,
            jobs.location,
            jobs.job_type
        FROM applications
        JOIN jobs ON applications.job_id = jobs.id
        WHERE applications.user_id = ?
        ORDER BY applications.applied_date DESC
    """, (user_id,)).fetchall()

    total_applications = len(applications)

    applied_count = sum(
        1 for app_item in applications
        if app_item["status"] == "Applied"
    )

    interview_count = sum(
        1 for app_item in applications
        if app_item["status"] == "Interview"
    )

    accepted_count = sum(
        1 for app_item in applications
        if app_item["status"] == "Accepted"
    )

    conn.close()

    return render_template(
        "dashboard.html",
        applications=applications,
        total_applications=total_applications,
        applied_count=applied_count,
        interview_count=interview_count,
        accepted_count=accepted_count
    )


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)