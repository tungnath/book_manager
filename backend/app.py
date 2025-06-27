import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)

CORS(app,
     origins="http://localhost:8081",
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Custom-Header"])


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'books.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Books table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS books (
            bid INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            owner TEXT NOT NULL
        )
    ''')

    # Check if 'favourite' column exists in books table
    cur.execute("PRAGMA table_info(books)")
    columns = [row[1] for row in cur.fetchall()]
    if 'favourite' not in columns:
        cur.execute("ALTER TABLE books ADD COLUMN favourite INTEGER DEFAULT 0")

    conn.commit()
    conn.close()

@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        username = data['username']
        password = data['password']
        print(username, password)
        role = 'admin' if username == 'admin' else 'user'

        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            cur = conn.cursor()
            res = cur.execute("SELECT * FROM users WHERE username=?", (username,))
            if cur.fetchone():
                return jsonify({'success': False, 'message': 'User exists'})

            cur.close()

            try:
                cur1 = conn.cursor()
                cur1.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                            (username, password, role))

                conn.commit()
                cur1.close()
            except Exception as e1:
                print("Signup insert error:", e1)
                traceback.print_exc()
                return jsonify({'success': False, 'message': 'User already exists'})


        return jsonify({'success': True, 'username': username, 'role': role}), 201

    except Exception as e:
        print("Signup error:", e)
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    print("flow")
    data = request.get_json()
    username = data['username']
    password = data['password']
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()

    if row:
        return jsonify({'authenticated': True, 'username': username, 'role': row[0]})
    else:
        return jsonify({'authenticated': False})
@app.route('/api/books/get', methods=['POST'])
def get_books():
    data = request.get_json()

    username = data.get('username')
    role = data.get('role')

    if not username or not role:
        return jsonify({'success': False, 'error': 'Missing username or role'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    if role == 'admin':
        cur.execute("SELECT * FROM books")
    else:
        cur.execute("SELECT * FROM books WHERE owner=?", (username,))
    books = [
        {
            'bid': row['bid'],
            'title': row['title'],
            'author': row['author'],
            'favourite': row['favourite'] if 'favourite' in row.keys() else 0
        }
        for row in cur.fetchall()
    ]
    conn.close()
    return jsonify(books)

@app.route('/api/books/favourite/<int:bid>', methods=['POST'])
def toggle_favourite_book(bid):
    data = request.get_json()
    username = data.get('username')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT favourite FROM books WHERE bid = ? AND owner = ?", (bid, username))
    row = c.fetchone()

    if not row:
        conn.close()
        return jsonify({'message': 'Book not found'}), 404

    new_status = 0 if row[0] == 1 else 1

    c.execute("UPDATE books SET favourite = ? WHERE bid = ? AND owner = ?", (new_status, bid, username))
    conn.commit()
    conn.close()

    message = "Removed from favourites" if new_status == 0 else "Book marked as favourite"
    return jsonify({'message': message})

@app.route('/api/books', methods=['POST'])
def add_book():
    data = request.get_json()
    title = data['title']
    author = data['author']
    owner = data['username']

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO books (title, author, owner) VALUES (?, ?, ?)",
                (title, author, owner))

    conn.commit()
    cur.close()

    conn.close()
    return jsonify({'success': True})

@app.route('/api/books/<int:bid>', methods=['PUT'])
def update_book(bid):
    data = request.get_json()
    title = data['title']
    author = data['author']

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE books SET title=?, author=? WHERE bid=?", (title, author, bid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/books/<int:bid>', methods=['DELETE'])
def delete_book(bid):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM books WHERE bid=?", (bid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/debug/books')
def debug_books():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()
    return jsonify(books)



if __name__ == '__main__':
    app.run(debug=True)