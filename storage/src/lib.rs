//! storage — SQLite backend via rusqlite (bundled).
//!
//! Supports dual journal modes:
//! - WAL mode (Native / Docker): fast concurrent reads
//! - Rollback/DELETE mode (WASI): no mmap/shm required

pub mod backend;
pub mod error;

pub use backend::StorageBackend;
pub use error::StorageError;
