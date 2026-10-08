use serde::{Deserialize, Serialize};

/// A persisted item record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Item {
    pub id: i64,
    pub name: String,
    pub value: f64,
    pub created_at: String,
}

/// Payload for creating a new item.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateItemRequest {
    pub name: String,
    pub value: f64,
}

/// Payload for updating an existing item.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateItemRequest {
    pub name: String,
    pub value: f64,
}
