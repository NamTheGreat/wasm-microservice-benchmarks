use core_domain::{fibonacci, Item};
use wasi::http::types::{
    Fields, IncomingRequest, OutgoingBody, OutgoingResponse, ResponseOutparam,
};

struct WasiHttpHandler;

impl wasi::exports::http::incoming_handler::Guest for WasiHttpHandler {
    fn handle(request: IncomingRequest, response_out: ResponseOutparam) {
        let path = request.path_with_query().unwrap_or_else(|| "/".to_string());
        let clean_path = path.split('?').next().unwrap_or("/");

        let (status_code, body_bytes) = if clean_path == "/health" {
            let json = serde_json::json!({
                "status": "ok",
                "target": "wasmtime"
            });
            (200, serde_json::to_vec(&json).unwrap())
        } else if clean_path.starts_with("/compute/") {
            let n_str = clean_path.trim_start_matches("/compute/");
            match n_str.parse::<u64>() {
                Ok(n) => {
                    let start = std::time::Instant::now();
                    let result = fibonacci(n);
                    let elapsed_us = start.elapsed().as_micros();
                    let json = serde_json::json!({
                        "input": n,
                        "result": result,
                        "elapsed_us": elapsed_us
                    });
                    (200, serde_json::to_vec(&json).unwrap())
                }
                Err(_) => (400, b"{\"error\":\"invalid number\"}".to_vec()),
            }
        } else if clean_path == "/items" {
            let mock_items: Vec<Item> = (1..=10)
                .map(|i| Item {
                    id: i,
                    name: format!("item-{}", i),
                    value: (i as f64) * 10.0,
                    created_at: "2026-10-09T00:00:00Z".to_string(),
                })
                .collect();
            (200, serde_json::to_vec(&mock_items).unwrap())
        } else if clean_path.starts_with("/items/") {
            let id_str = clean_path.trim_start_matches("/items/");
            match id_str.parse::<i64>() {
                Ok(id) => {
                    let item = Item {
                        id,
                        name: format!("item-{}", id),
                        value: (id as f64) * 10.0,
                        created_at: "2026-10-09T00:00:00Z".to_string(),
                    };
                    (200, serde_json::to_vec(&item).unwrap())
                }
                Err(_) => (400, b"{\"error\":\"invalid id\"}".to_vec()),
            }
        } else {
            (404, b"{\"error\":\"not found\"}".to_vec())
        };

        let headers = Fields::new();
        let ct_name = "content-type".to_string();
        let _ = headers.set(&ct_name, &[b"application/json".to_vec()]);

        let response = OutgoingResponse::new(headers);
        let _ = response.set_status_code(status_code);

        let body = response.body().expect("response body");
        let stream = body.write().expect("body write stream");
        let _ = stream.blocking_write_and_flush(&body_bytes);
        drop(stream);
        let _ = OutgoingBody::finish(body, None);

        ResponseOutparam::set(response_out, Ok(response));
    }
}

wasi::http::proxy::export!(WasiHttpHandler);
