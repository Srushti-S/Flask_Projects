CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    nickname TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    joke_balance INTEGER DEFAULT 0,
    role TEXT DEFAULT 'User'
);


CREATE TABLE IF NOT EXISTS joke (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE IF NOT EXISTS rating (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    joke_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    FOREIGN KEY (joke_id) REFERENCES joke (id),
    FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE IF NOT EXISTS taken_jokes (
    user_id INTEGER NOT NULL,
    joke_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, joke_id),
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (joke_id) REFERENCES joke (id)
);

CREATE TABLE IF NOT EXISTS viewed_jokes (
    user_id INTEGER NOT NULL,
    joke_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, joke_id),
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (joke_id) REFERENCES joke (id)
);
