//! wasi_adapter — stub binary for wasm32-wasip2.
//!
//! Phase 1: compile-check stub only. Full wasi:http/incoming-handler wiring
//! is a Phase 2 task once cargo-component / wit-bindgen integration is set up.

fn main() {
    // This stub is intentionally minimal. The wasm32-wasip2 target does not
    // support std networking or tokio. Full HTTP handling via wasi:http will
    // be wired in Phase 2 using cargo-component and wit-bindgen.
    let _ = core_domain::fibonacci(10); // smoke-test the domain dependency
}
