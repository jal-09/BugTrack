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


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "bugtrack-development-secret-key"
)

# Use the database located in the same folder as app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not name or not email or not password or not confirm_password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("register"))

        # Hash password before saving
        hashed_password = generate_password_hash(password)

        connection = get_db_connection()

        # Check duplicate email
        existing_user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            connection.close()
            flash("An account with this email already exists.")
            return redirect(url_for("register"))

        # Create normal user
        connection.execute(
            """
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                email,
                hashed_password,
                "user"
            )
        )

        connection.commit()
        connection.close()

        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    # If already logged in, redirect to correct dashboard
    if "user_id" in session:

        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.")
            return redirect(url_for("login"))

        connection = get_db_connection()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        # Check user exists and password is correct
        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            # Admin login
            if user["role"] == "admin":
                return redirect(
                    url_for("admin_dashboard")
                )

            # Normal user login
            return redirect(
                url_for("dashboard")
            )

        flash("Invalid email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


# --------------------------------------------------
# USER DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
def dashboard():

    # User must be logged in
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    # Admin should not access normal user dashboard
    if session.get("role") == "admin":
        return redirect(
            url_for("admin_dashboard")
        )

    connection = get_db_connection()

    # Only display bugs created by logged-in user
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


# --------------------------------------------------
# REPORT BUG
# --------------------------------------------------

@app.route("/report-bug", methods=["GET", "POST"])
def report_bug():

    # User must be logged in
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    # Admin cannot report bugs through user page
    if session.get("role") == "admin":
        return redirect(
            url_for("admin_dashboard")
        )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        priority = request.form.get(
            "priority",
            ""
        ).strip()

        # Basic validation
        if not title or not description:
            flash(
                "Title and description are required."
            )
            return redirect(
                url_for("report_bug")
            )

        if len(title) < 3:
            flash(
                "Bug title must be at least 3 characters."
            )
            return redirect(
                url_for("report_bug")
            )

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
            flash(
                "Please select a valid category."
            )
            return redirect(
                url_for("report_bug")
            )

        if priority not in valid_priorities:
            flash(
                "Please select a valid priority."
            )
            return redirect(
                url_for("report_bug")
            )

        connection = get_db_connection()

        # Save bug into database
        connection.execute(
            """
            INSERT INTO bugs
            (
                title,
                description,
                category,
                priority,
                status,
                reporter_id
            )
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

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "report_bug.html"
    )


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin")
def admin_dashboard():

    # Must be logged in
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    # Must be admin
    if session.get("role") != "admin":
        flash("Administrator access required.")
        return redirect(
            url_for("dashboard")
        )

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


# --------------------------------------------------
# ADMIN MANAGE BUG
# --------------------------------------------------

@app.route(
    "/admin/bug/<int:bug_id>",
    methods=["GET", "POST"]
)
def manage_bug(bug_id):

    # Must be logged in
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    # Must be admin
    if session.get("role") != "admin":
        flash("Administrator access required.")
        return redirect(
            url_for("dashboard")
        )

    connection = get_db_connection()

    bug = connection.execute(
        """
        SELECT *
        FROM bugs
        WHERE id = ?
        """,
        (bug_id,)
    ).fetchone()

    # Bug does not exist
    if bug is None:
        connection.close()

        flash("Bug not found.")

        return redirect(
            url_for("admin_dashboard")
        )

    if request.method == "POST":

        priority = request.form.get(
            "priority",
            ""
        ).strip()

        status = request.form.get(
            "status",
            ""
        ).strip()

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

        # Validate priority
        if priority not in valid_priorities:

            connection.close()

            flash("Invalid priority.")

            return redirect(
                url_for(
                    "manage_bug",
                    bug_id=bug_id
                )
            )

        # Validate status
        if status not in valid_statuses:

            connection.close()

            flash("Invalid status.")

            return redirect(
                url_for(
                    "manage_bug",
                    bug_id=bug_id
                )
            )

        # Update bug
        connection.execute(
            """
            UPDATE bugs

            SET
                priority = ?,
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

        return redirect(
            url_for("admin_dashboard")
        )

    connection.close()

    return render_template(
        "manage_bug.html",
        bug=bug
    )


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out."
    )

    return redirect(
        url_for("login")
    )


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)