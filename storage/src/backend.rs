use rusqlite::{params, Connection};

use core_domain::{CreateItemRequest, Item, UpdateItemRequest};

use crate::StorageError;

/// SQLite-backed item store.
///
/// Use [`StorageBackend::open`] to create an instance.
/// Pass `wal = true` for Native/Docker targets (better concurrency).
/// Pass `wal = false` for WASI targets (no mmap/shm support).
pub struct StorageBackend {
    conn: Connection,
}

impl StorageBackend {
    /// Open (or create) a SQLite database at `path`.
    ///
    /// `wal = true` enables WAL journal mode + NORMAL synchronous.
    /// `wal = false` leaves the default DELETE journal mode for WASI compat.
    pub fn open(path: &str, wal: bool) -> Result<Self, StorageError> {
        let mut conn = Connection::open(path)?;

        if wal {
            conn.execute_batch(
                "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
            )?;
        }

        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                value       REAL    NOT NULL DEFAULT 0.0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_items_name ON items(name);",
        )?;

        // Ensure 10 baseline seeded items exist for consistent multi-target benchmarking
        let count: i64 = conn.query_row("SELECT count(*) FROM items", [], |r| r.get(0))?;
        if count == 0 {
            let tx = conn.transaction()?;
            {
                let mut stmt = tx.prepare("INSERT INTO items (id, name, value, created_at) VALUES (?1, ?2, ?3, '2026-10-09T00:00:00Z')")?;
                for i in 1..=10 {
                    stmt.execute(params![i as i64, format!("item-{}", i), (i as f64) * 10.0])?;
                }
            }
            tx.commit()?;
        }

        Ok(Self { conn })
    }

    /// Return all items.
    pub fn list_items(&self) -> Result<Vec<Item>, StorageError> {
        let mut stmt = self.conn.prepare(
            "SELECT id, name, value, created_at FROM items ORDER BY id",
        )?;
        let items = stmt
            .query_map([], |row| {
                Ok(Item {
                    id: row.get(0)?,
                    name: row.get(1)?,
                    value: row.get(2)?,
                    created_at: row.get(3)?,
                })
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(items)
    }

    /// Return a single item by `id`, or `StorageError::NotFound`.
    pub fn get_item(&self, id: i64) -> Result<Item, StorageError> {
        let result = self.conn.query_row(
            "SELECT id, name, value, created_at FROM items WHERE id = ?1",
            params![id],
            |row| {
                Ok(Item {
                    id: row.get(0)?,
                    name: row.get(1)?,
                    value: row.get(2)?,
                    created_at: row.get(3)?,
                })
            },
        );
        match result {
            Ok(item) => Ok(item),
            Err(rusqlite::Error::QueryReturnedNoRows) => Err(StorageError::NotFound(id)),
            Err(e) => Err(StorageError::Sqlite(e)),
        }
    }

    /// Insert a new item and return it with the assigned `id` and `created_at`.
    pub fn create_item(&self, req: &CreateItemRequest) -> Result<Item, StorageError> {
        self.conn.execute(
            "INSERT INTO items (name, value) VALUES (?1, ?2)",
            params![req.name, req.value],
        )?;
        let id = self.conn.last_insert_rowid();
        self.get_item(id)
    }

    /// Update an existing item and return it, or `StorageError::NotFound`.
    pub fn update_item(&self, id: i64, req: &UpdateItemRequest) -> Result<Item, StorageError> {
        let rows = self.conn.execute(
            "UPDATE items SET name = ?1, value = ?2 WHERE id = ?3",
            params![req.name, req.value, id],
        )?;
        if rows == 0 {
            return Err(StorageError::NotFound(id));
        }
        self.get_item(id)
    }

    /// Delete an item by `id`. Returns `StorageError::NotFound` if no row existed.
    pub fn delete_item(&self, id: i64) -> Result<(), StorageError> {
        let rows = self.conn.execute(
            "DELETE FROM items WHERE id = ?1",
            params![id],
        )?;
        if rows == 0 {
            return Err(StorageError::NotFound(id));
        }
        Ok(())
    }
}
