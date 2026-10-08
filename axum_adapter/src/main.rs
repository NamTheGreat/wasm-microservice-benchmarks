use std::sync::{Arc, Mutex};
use std::time::Instant;

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use serde::Serialize;
use tokio::net::TcpListener;

use core_domain::{CreateItemRequest, UpdateItemRequest, fibonacci};
use storage::{StorageBackend, StorageError};

// ---------------------------------------------------------------------------
// Shared application state — Mutex because rusqlite::Connection is !Sync
// ---------------------------------------------------------------------------

struct AppState {
    db: Mutex<StorageBackend>,
    target: String,
}

type SharedState = Arc<AppState>;

// ---------------------------------------------------------------------------
// Uniform error response
// ---------------------------------------------------------------------------

struct AppError(StatusCode, String);

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let body = serde_json::json!({"error": self.1});
        (self.0, Json(body)).into_response()
    }
}

fn storage_err(e: StorageError) -> AppError {
    match e {
        StorageError::NotFound(id) => AppError(
            StatusCode::NOT_FOUND,
            format!("item {} not found", id),
        ),
        other => AppError(
            StatusCode::INTERNAL_SERVER_ERROR,
            other.to_string(),
        ),
    }
}

// ---------------------------------------------------------------------------
// Handler: GET /health
// ---------------------------------------------------------------------------

#[derive(Serialize)]
struct HealthResponse {
    status: &'static str,
    target: String,
}

async fn health(State(state): State<SharedState>) -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        target: state.target.clone(),
    })
}

// ---------------------------------------------------------------------------
// Handler: GET /items
// ---------------------------------------------------------------------------

async fn list_items(State(state): State<SharedState>) -> Result<Json<serde_json::Value>, AppError> {
    let db = state.db.lock().unwrap();
    let items = db.list_items().map_err(storage_err)?;
    Ok(Json(serde_json::to_value(items).unwrap()))
}

// ---------------------------------------------------------------------------
// Handler: GET /items/:id
// ---------------------------------------------------------------------------

async fn get_item(
    State(state): State<SharedState>,
    Path(id): Path<i64>,
) -> Result<Json<serde_json::Value>, AppError> {
    let db = state.db.lock().unwrap();
    let item = db.get_item(id).map_err(storage_err)?;
    Ok(Json(serde_json::to_value(item).unwrap()))
}

// ---------------------------------------------------------------------------
// Handler: POST /items  → 201
// ---------------------------------------------------------------------------

async fn create_item(
    State(state): State<SharedState>,
    Json(req): Json<CreateItemRequest>,
) -> Result<Response, AppError> {
    let db = state.db.lock().unwrap();
    let item = db.create_item(&req).map_err(storage_err)?;
    let body = Json(serde_json::to_value(item).unwrap());
    Ok((StatusCode::CREATED, body).into_response())
}

// ---------------------------------------------------------------------------
// Handler: PUT /items/:id
// ---------------------------------------------------------------------------

async fn update_item(
    State(state): State<SharedState>,
    Path(id): Path<i64>,
    Json(req): Json<UpdateItemRequest>,
) -> Result<Json<serde_json::Value>, AppError> {
    let db = state.db.lock().unwrap();
    let item = db.update_item(id, &req).map_err(storage_err)?;
    Ok(Json(serde_json::to_value(item).unwrap()))
}

// ---------------------------------------------------------------------------
// Handler: DELETE /items/:id  → 204
// ---------------------------------------------------------------------------

async fn delete_item(
    State(state): State<SharedState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let db = state.db.lock().unwrap();
    db.delete_item(id).map_err(storage_err)?;
    Ok(StatusCode::NO_CONTENT)
}

// ---------------------------------------------------------------------------
// Handler: GET /compute/:n
// ---------------------------------------------------------------------------

#[derive(Serialize)]
struct ComputeResponse {
    input: u64,
    result: u64,
    elapsed_us: u128,
}

async fn compute(Path(n): Path<u64>) -> Json<ComputeResponse> {
    let start = Instant::now();
    let result = fibonacci(n);
    let elapsed_us = start.elapsed().as_micros();
    Json(ComputeResponse {
        input: n,
        result,
        elapsed_us,
    })
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    let target = std::env::var("TARGET_NAME").unwrap_or_else(|_| "native".to_string());
    let db_path = std::env::var("DB_PATH").unwrap_or_else(|_| "bench.db".to_string());
    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string());

    tracing::info!(target = %target, db = %db_path, port = %port, "starting axum_adapter");

    let db = StorageBackend::open(&db_path, true).expect("failed to open SQLite database");

    let state: SharedState = Arc::new(AppState {
        db: Mutex::new(db),
        target,
    });

    let app = Router::new()
        .route("/health", get(health))
        .route("/items", get(list_items).post(create_item))
        .route("/items/{id}", get(get_item).put(update_item).delete(delete_item))
        .route("/compute/{n}", get(compute))
        .with_state(state);

    let addr = format!("0.0.0.0:{port}");
    tracing::info!("listening on {}", addr);
    let listener = TcpListener::bind(&addr).await.expect("bind failed");
    axum::serve(listener, app).await.expect("server error");
}
