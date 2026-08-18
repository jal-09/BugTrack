import sqlite3
from werkzeug.security import generate_password_hash

connection = sqlite3.connect("database.db")

name = "BugTrack Admin"
email = "admin@bugtrack.com"
password = generate_password_hash("admin123")

existing_admin = connection.execute(
    "SELECT * FROM users WHERE email = ?",
    (email,)
).fetchone()

if existing_admin:
    print("Admin account already exists.")
else:
    connection.execute(
        """
        INSERT INTO users (name, email, password, role)
        VALUES (?, ?, ?, ?)
        """,
        (name, email, password, "admin")
    )

    connection.commit()
    print("Admin account created successfully.")

connection.close()