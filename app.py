import os
import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "bugtrack-development-secret-key"
)


def get_db_connection():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not name or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()

        existing_user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            connection.close()
            flash("An account with this email already exists.")
            return redirect(url_for("register"))

        connection.execute(
            """
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, hashed_password, "user")
        )

        connection.commit()
        connection.close()

        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not email or not password:
            flash("Email and password are required.")
            return redirect(url_for("login"))

        connection = get_db_connection()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    connection = get_db_connection()

    bugs = connection.execute(
        """
        SELECT *
        FROM bugs
        WHERE reporter_id = ?
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        name=session["user_name"],
        bugs=bugs
    )

    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    return render_template(
        "dashboard.html",
        name=session["user_name"]
    )


@app.route("/logout")
def logout():

    session.clear()
    flash("You have been logged out.")

    return redirect(url_for("login"))

@app.route("/report-bug", methods=["GET", "POST"])
def report_bug():

    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"].strip()
        description = request.form["description"].strip()
        category = request.form["category"]
        priority = request.form["priority"]

        if not title or not description:
            flash("Title and description are required.")
            return redirect(url_for("report_bug"))

        if len(title) < 3:
            flash("Bug title must be at least 3 characters.")
            return redirect(url_for("report_bug"))

        valid_categories = [
            "UI",
            "Functionality",
            "Performance",
            "Security",
            "Other"
        ]

        valid_priorities = [
            "Low",
            "Medium",
            "High"
        ]

        if category not in valid_categories:
            flash("Please select a valid category.")
            return redirect(url_for("report_bug"))

        if priority not in valid_priorities:
            flash("Please select a valid priority.")
            return redirect(url_for("report_bug"))

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO bugs
            (title, description, category, priority, status, reporter_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                description,
                category,
                priority,
                "Open",
                session["user_id"]
            )
        )

        connection.commit()
        connection.close()

        flash("Bug reported successfully.")

        return redirect(url_for("dashboard"))

    return render_template("report_bug.html")
@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    bugs = connection.execute(
        """
        SELECT
            bugs.*,
            users.name AS reporter_name,
            assigned_user.name AS assigned_name
        FROM bugs
        JOIN users
            ON bugs.reporter_id = users.id
        LEFT JOIN users AS assigned_user
            ON bugs.assigned_to = assigned_user.id
        ORDER BY bugs.created_at DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        bugs=bugs,
        name=session["user_name"]
    )
@app.route("/admin/bug/<int:bug_id>", methods=["GET", "POST"])
def manage_bug(bug_id):

    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Administrator access required.")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    bug = connection.execute(
        """
        SELECT *
        FROM bugs
        WHERE id = ?
        """,
        (bug_id,)
    ).fetchone()

    if bug is None:
        connection.close()
        flash("Bug not found.")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":

        priority = request.form["priority"]
        status = request.form["status"]

        valid_priorities = [
            "Low",
            "Medium",
            "High"
        ]

        valid_statuses = [
            "Open",
            "In Progress",
            "Resolved"
        ]

        if priority not in valid_priorities:
            connection.close()
            flash("Invalid priority.")
            return redirect(
                url_for("manage_bug", bug_id=bug_id)
            )

        if status not in valid_statuses:
            connection.close()
            flash("Invalid status.")
            return redirect(
                url_for("manage_bug", bug_id=bug_id)
            )

        connection.execute(
            """
            UPDATE bugs
            SET priority = ?,
                status = ?,
                assigned_to = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                priority,
                status,
                session["user_id"],
                bug_id
            )
        )

        connection.commit()
        connection.close()

        flash("Bug updated successfully.")

        return redirect(url_for("admin_dashboard"))

    connection.close()

    return render_template(
        "manage_bug.html",
        bug=bug
    )
if __name__ == "__main__":
    app.run(debug=True)