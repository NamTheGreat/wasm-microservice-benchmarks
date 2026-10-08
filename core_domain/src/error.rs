use thiserror::Error;

#[derive(Debug, Error)]
pub enum DomainError {
    #[error("item not found: id={0}")]
    NotFound(i64),
    #[error("invalid input: {0}")]
    InvalidInput(String),
}
