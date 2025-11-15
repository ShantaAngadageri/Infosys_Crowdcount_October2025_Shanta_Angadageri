import sqlite3

connection = sqlite3.connect('LoginData.db')
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS USERS (
    first_name TEXT,
    last_name TEXT,
    email TEXT PRIMARY KEY,
    password TEXT NOT NULL
)
""")

cursor.execute("""
INSERT OR IGNORE INTO USERS (first_name, last_name, email, password)
VALUES ('tester', 'test', 'tester@gmail.com', 'tester123')
""")

connection.commit()
connection.close()
print("Database and user created successfully!")
