//! core_domain — pure domain types and logic, zero I/O.

pub mod item;
pub mod compute;
pub mod error;

pub use item::{Item, CreateItemRequest, UpdateItemRequest};
pub use compute::fibonacci;
pub use error::DomainError;
