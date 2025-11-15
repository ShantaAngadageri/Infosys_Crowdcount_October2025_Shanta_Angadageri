import sqlite3

connection = sqlite3.connect('LoginData.db')
cursor = connection.cursor()

# Create STUDENT table if it does not already exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS STUDENT (
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user'
)
""")

# Insert a default user if it does not already exist
cursor.execute("""
INSERT OR IGNORE INTO STUDENT (first_name, last_name, email, password, role)
VALUES ('tester', 'test', 'tester@gmail.com', 'tester123', 'admin')
""")
cursor.execute("""
INSERT OR IGNORE INTO STUDENT (first_name, last_name, email, password, role)
VALUES ('Shanta', 'Angadageri', 'shantaangadageri@gmail.com', 'Shanta@123', 'admin')
""")
cursor.execute("""
INSERT OR IGNORE INTO STUDENT (first_name, last_name, email, password, role)
VALUES ('Sujata', 'A', 'shantaangadageri86@gmail.com', 'Shanta@123', 'user')
""")

cursor.execute("""
INSERT OR IGNORE INTO STUDENT (first_name, last_name, email, password, role)
VALUES ('Sneha', 'A', 'shantasabappa@gmail.com', 'Shanta@123', 'user')
""")

connection.commit()
connection.close()
print("Database and STUDENT table initialized successfully!")
