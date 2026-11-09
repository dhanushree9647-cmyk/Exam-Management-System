import mysql.connector
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

cursor = db.cursor()

username = "admin"
password = "Admin@123"

hashed_password = generate_password_hash(password)

cursor.execute(
    "INSERT INTO admins (username, password) VALUES (%s, %s)",
    (username, hashed_password)
)

db.commit()

print("Admin account created successfully!")

cursor.close()
db.close()