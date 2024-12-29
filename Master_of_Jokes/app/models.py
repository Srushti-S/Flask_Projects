import sqlite3
from flask import current_app, g

def add_user(email, nickname, password):
    db = get_db()
    try:
        db.execute(
            'INSERT INTO user (email, nickname, password) VALUES (?, ?, ?)',
            (email, nickname, password)
        )
        db.commit()
        return True
    except db.IntegrityError:
        return False

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))

def init_app(app):
    app.teardown_appcontext(close_db)

def get_user_by_email(email):
    db = get_db()
    user = db.execute(
        'SELECT * FROM user WHERE email = ?', (email,)
    ).fetchone()
    return user

def get_jokes_by_user(user_id):
    db = get_db()
    jokes = db.execute(
        'SELECT * FROM joke WHERE author_id = ?',
        (user_id,)
    ).fetchall()
    return jokes

def is_nickname_unique(nickname):
    db = get_db()
    result = db.execute(
        'SELECT id FROM user WHERE nickname = ?', (nickname,)
    ).fetchone()
    return result is None 

def get_user_by_email_or_nickname(identity):
    db = get_db()
    user = db.execute(
        'SELECT * FROM user WHERE email = ? OR nickname = ?',
        (identity, identity)
    ).fetchone()
    return user

def add_joke(title, body, author_id):
    db = get_db()
    try:
        db.execute(
            'INSERT INTO joke (title, body, author_id) VALUES (?, ?, ?)',
            (title, body, author_id)
        )
        db.commit()
        increment_joke_balance(author_id)
        return True
    except db.IntegrityError:
        return False

def is_joke_title_unique(title, author_id):
    db = get_db()
    result = db.execute(
        'SELECT id FROM joke WHERE title = ? AND author_id = ?',
        (title, author_id)
    ).fetchone()
    return result is None  

def get_joke_balance(user_id):
    db = get_db()
    result = db.execute(
        'SELECT joke_balance FROM user WHERE id = ?',
        (user_id,)
    ).fetchone()
    return result['joke_balance'] if result else 0

def increment_joke_balance(user_id):
    db = get_db()
    db.execute(
        'UPDATE user SET joke_balance = joke_balance + 1 WHERE id = ?',
        (user_id,)
    )
    db.commit()

def get_jokes_by_user_with_ratings(user_id):
    db = get_db()
    jokes = db.execute('''
        SELECT 
            j.id, 
            j.title, 
            j.body, 
            IFNULL(AVG(r.rating), 0) AS avg_rating,
            u.nickname AS author_nickname,
            CASE WHEN j.author_id = ? THEN 'authored' ELSE 'taken' END AS joke_type
        FROM joke j
        LEFT JOIN rating r ON j.id = r.joke_id
        LEFT JOIN user u ON j.author_id = u.id
        LEFT JOIN taken_jokes t ON j.id = t.joke_id
        WHERE j.author_id = ? OR t.user_id = ?
        GROUP BY j.id
    ''', (user_id, user_id, user_id)).fetchall()
    return jokes


def get_joke_by_id(joke_id):
    db = get_db()
    joke = db.execute('''
        SELECT j.id, j.title, j.body, j.author_id, j.created_at, u.nickname
        FROM joke j
        JOIN user u ON j.author_id = u.id
        WHERE j.id = ?
    ''', (joke_id,)).fetchone()
    return joke


def update_joke_body(joke_id, new_body, user_id=None):
    db = get_db()
    if user_id:
        db.execute(
            'UPDATE joke SET body = ? WHERE id = ? AND author_id = ?',
            (new_body, joke_id, user_id)
        )
    else:
        db.execute(
            'UPDATE joke SET body = ? WHERE id = ?',
            (new_body, joke_id)
        )
    db.commit()

def get_moderator_count():
    """Returns the number of users in the Moderator role."""
    db = get_db()
    result = db.execute('SELECT COUNT(*) FROM user WHERE role = ?', ('Moderator',)).fetchone()
    return result[0] if result else 0

# def get_moderator_count():
#     db = get_db()
#     count = db.execute('SELECT COUNT(*) FROM user WHERE role = "Moderator"').fetchone()[0]
#     return count

def add_user_to_role(user_id, role):
    db = get_db()
    db.execute('UPDATE user SET role = ? WHERE id = ?', (role, user_id))
    db.commit()

def remove_user_from_role(user_id, role):
    db = get_db()
    db.execute('UPDATE user SET role = NULL WHERE id = ? AND role = ?', (user_id, role))
    db.commit()

def get_non_authored_jokes(user_id):
    db = get_db()
    jokes = db.execute('''
        SELECT 
            j.id, 
            j.title, 
            u.nickname AS author_nickname, 
            IFNULL(AVG(r.rating), 0) AS avg_rating
        FROM joke j
        JOIN user u ON j.author_id = u.id
        LEFT JOIN rating r ON j.id = r.joke_id
        WHERE j.author_id != ?
        GROUP BY j.id
    ''', (user_id,)).fetchall()
    return jokes


def has_user_taken_joke(user_id, joke_id):
    db = get_db()
    result = db.execute(
        'SELECT 1 FROM taken_jokes WHERE user_id = ? AND joke_id = ?',
        (user_id, joke_id)
    ).fetchone()
    return result is not None  

def mark_joke_as_taken(user_id, joke_id):
    db = get_db()
    db.execute(
        'INSERT INTO taken_jokes (user_id, joke_id) VALUES (?, ?)',
        (user_id, joke_id)
    )
    db.commit()

def delete_joke(joke_id):
    db = get_db()
    db.execute('DELETE FROM joke WHERE id = ?', (joke_id,))
    db.commit()

def add_joke_rating(joke_id, user_id, rating):
    db = get_db()
    db.execute(
        'INSERT INTO rating (joke_id, user_id, rating) VALUES (?, ?, ?)',
        (joke_id, user_id, rating)
    )
    db.commit()

def get_average_rating(joke_id):
    db = get_db()
    result = db.execute(
        'SELECT AVG(rating) as avg_rating FROM rating WHERE joke_id = ?', 
        (joke_id,)
    ).fetchone()
    return result['avg_rating'] if result['avg_rating'] is not None else 0

def has_user_viewed_joke(user_id, joke_id):
    db = get_db()
    result = db.execute(
        'SELECT 1 FROM viewed_jokes WHERE user_id = ? AND joke_id = ?', 
        (user_id, joke_id)
    ).fetchone()
    return result is not None

def mark_joke_as_viewed(user_id, joke_id):
    db = get_db()
    db.execute('INSERT INTO viewed_jokes (user_id, joke_id) VALUES (?, ?)', (user_id, joke_id))
    db.execute('UPDATE user SET joke_balance = joke_balance - 1 WHERE id = ?', (user_id,))
    db.commit()

def get_all_jokes(user_id=None):
    db = get_db()
    query = '''
        SELECT 
            j.id, 
            j.title, 
            j.body, 
            MAX(u.nickname) AS nickname, 
            j.created_at, 
            IFNULL(AVG(r.rating), 0) AS avg_rating
        FROM joke j
        LEFT JOIN user u ON j.author_id = u.id
        LEFT JOIN rating r ON j.id = r.joke_id
    '''
    if user_id is not None:
        query += '''
            WHERE j.author_id != ?
        '''
    query += '''
        GROUP BY j.id;
    '''
    if user_id is not None:
        jokes = db.execute(query, (user_id,)).fetchall()
    else:
        jokes = db.execute(query).fetchall()
    return jokes


def set_user_role(user_id, role):
    db = get_db()
    db.execute('UPDATE user SET role = ? WHERE id = ?', (role, user_id))
    db.commit()

def get_user_role(user_id):
    db = get_db()
    result = db.execute('SELECT role FROM user WHERE id = ?', (user_id,)).fetchone()
    return result['role'] if result else None

def get_all_users():
    db = get_db()
    users = db.execute('SELECT id, email, nickname, role, joke_balance FROM user').fetchall()
    return users

def update_user_role(user_id, role):
    """
    Update the role of a user in the database.
    Args:
        user_id: The ID of the user.
        role: The new role to assign to the user.
    """
    db = get_db()
    try:
        db.execute(
            'UPDATE user SET role = ? WHERE id = ?',
            (role, user_id)
        )
        db.commit()
    except Exception as e:
        print(f"Error updating user role: {e}")
        raise
