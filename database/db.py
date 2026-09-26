import sqlite3
import os

# DB_PATH can point at a persistent disk / volume on the hosting platform,
# otherwise the database lives next to this file.
DB_PATH = os.environ.get('DB_PATH') or os.path.join(os.path.dirname(__file__), 'edutrack.db')

def get_connection():
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    # SQLite ignores FOREIGN KEY / ON DELETE CASCADE unless this is switched on per connection
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            marks REAL NOT NULL CHECK(marks >= 0 AND marks <= 100),
            semester TEXT DEFAULT 'Semester 1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            semester TEXT NOT NULL DEFAULT 'Semester 1',
            target REAL NOT NULL CHECK(target >= 0 AND target <= 100),
            UNIQUE(user_id, subject, semester),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            exam_time TEXT,
            venue TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    ''')

    migrate_targets_semester(conn)
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def migrate_targets_semester(conn):
    """Older databases stored one target per subject. Rebuild the table so a
    target belongs to a (subject, semester) pair, keeping existing targets.
    The semester is taken from the matching marks row when one exists."""
    columns = [row['name'] for row in conn.execute("PRAGMA table_info(targets)")]
    if 'semester' in columns:
        return
    # Foreign key checks are paused while the table is rebuilt (standard SQLite practice)
    conn.executescript('''
        PRAGMA foreign_keys = OFF;
        ALTER TABLE targets RENAME TO targets_old;

        CREATE TABLE targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            semester TEXT NOT NULL DEFAULT 'Semester 1',
            target REAL NOT NULL CHECK(target >= 0 AND target <= 100),
            UNIQUE(user_id, subject, semester),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        INSERT OR IGNORE INTO targets (user_id, subject, semester, target)
        SELECT t.user_id, t.subject,
               COALESCE((SELECT m.semester FROM marks m
                         WHERE m.user_id = t.user_id AND m.subject = t.subject
                         ORDER BY m.created_at DESC LIMIT 1), 'Semester 1'),
               t.target
        FROM targets_old t;

        DROP TABLE targets_old;
        PRAGMA foreign_keys = ON;
    ''')

if __name__ == '__main__':
    init_db()
