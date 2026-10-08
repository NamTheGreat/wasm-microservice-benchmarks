.PHONY: all build-native build-docker build-wasm build-spin clean

all: build-native build-wasm

build-native:
	cargo build --release -p axum_adapter

build-docker:
	docker build -t wasm-bench-server:latest .

build-wasm:
	cargo build --release -p wasi_adapter --target wasm32-wasip2

build-spin:
	spin build

clean:
	cargo clean
