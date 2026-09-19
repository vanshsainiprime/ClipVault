import sqlite3
from pathlib import Path


class Database:
    """Local SQLite storage for ClipVault."""

    def __init__(self, max_items=1000):
        self.max_items = max_items

        data_dir = (
            Path.home()
            / ".local"
            / "share"
            / "clipvault"
        )

        data_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.db_path = data_dir / "clipboard.db"

        self.connection = sqlite3.connect(
            self.db_path
        )

        self.connection.row_factory = sqlite3.Row

        self._create_tables()

    def _create_tables(self):
        """Create the database tables and indexes."""

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS clipboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pinned INTEGER DEFAULT 0
            )
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_clipboard_created
            ON clipboard(created_at DESC)
            """
        )

        self.connection.commit()

    def add(self, content):
        """Add new clipboard content.

        Returns True if a new entry was created.
        """

        if not content:
            return False

        latest = self.connection.execute(
            """
            SELECT content
            FROM clipboard
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        # Ignore consecutive duplicates.
        if latest and latest["content"] == content:
            return False

        self.connection.execute(
            """
            INSERT INTO clipboard (content)
            VALUES (?)
            """,
            (content,),
        )

        self.connection.commit()

        self._enforce_limit()

        return True

    def _enforce_limit(self):
        """Keep the database within the history limit."""

        self.connection.execute(
            """
            DELETE FROM clipboard
            WHERE id NOT IN (
                SELECT id
                FROM clipboard
                ORDER BY pinned DESC, id DESC
                LIMIT ?
            )
            """,
            (self.max_items,),
        )

        self.connection.commit()

    def get_recent(self, limit=20):
        """Return recent clipboard entries."""

        return self.connection.execute(
            """
            SELECT
                id,
                content,
                created_at,
                pinned
            FROM clipboard
            ORDER BY pinned DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    def get_by_id(self, entry_id):
        """Return a clipboard entry by ID."""

        return self.connection.execute(
            """
            SELECT
                id,
                content,
                created_at,
                pinned
            FROM clipboard
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()

    def search(self, query, limit=50):
        """Search clipboard history."""

        return self.connection.execute(
            """
            SELECT
                id,
                content,
                created_at,
                pinned
            FROM clipboard
            WHERE content LIKE ?
            ORDER BY pinned DESC, id DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        ).fetchall()

    def delete(self, entry_id):
        """Delete one clipboard entry.

        Returns True if an entry was deleted.
        """

        cursor = self.connection.execute(
            """
            DELETE FROM clipboard
            WHERE id = ?
            """,
            (entry_id,),
        )

        self.connection.commit()

        return cursor.rowcount > 0

    def pin(self, entry_id):
        """Pin one clipboard entry."""

        cursor = self.connection.execute(
            """
            UPDATE clipboard
            SET pinned = 1
            WHERE id = ?
            """,
            (entry_id,),
        )

        self.connection.commit()

        return cursor.rowcount > 0

    def unpin(self, entry_id):
        """Unpin one clipboard entry."""

        cursor = self.connection.execute(
            """
            UPDATE clipboard
            SET pinned = 0
            WHERE id = ?
            """,
            (entry_id,),
        )

        self.connection.commit()

        return cursor.rowcount > 0

    def clear(self):
        """Delete all unpinned entries.

        Returns the number of deleted entries.
        """

        cursor = self.connection.execute(
            """
            DELETE FROM clipboard
            WHERE pinned = 0
            """
        )

        self.connection.commit()

        return cursor.rowcount

    def count(self):
        """Return the total number of clipboard entries."""

        result = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM clipboard
            """
        ).fetchone()

        return result[0]

    def close(self):
        """Close the database connection."""

        self.connection.close()
