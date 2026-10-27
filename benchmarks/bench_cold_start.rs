use std::env;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::process::{Command, Stdio};
use std::thread::sleep;
use std::time::{Duration, Instant};

fn measure_cold_start(cmd_str: &str, port: u16) -> f64 {
    let start = Instant::now();

    let mut child = Command::new("sh")
        .arg("-c")
        .arg(cmd_str)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .unwrap_or_else(|e| panic!("Failed to spawn command '{}': {}", cmd_str, e));

    let addr = format!("127.0.0.1:{}", port);
    
    let mut stream = loop {
        if let Ok(s) = TcpStream::connect(&addr) {
            break s;
        }
        if start.elapsed().as_secs() > 10 {
            let _ = child.kill();
            let _ = child.wait();
            panic!("Process startup timeout (>10s) for command '{}'", cmd_str);
        }
        sleep(Duration::from_micros(100));
    };

    stream
        .write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        .expect("Failed to write to TCP stream");

    let mut buf = [0u8; 64];
    let bytes_read = stream.read(&mut buf).expect("Failed to read response");
    let duration_micros = start.elapsed().as_micros();

    let response_str = String::from_utf8_lossy(&buf[..bytes_read]);
    if !response_str.contains("200") {
        let _ = child.kill();
        let _ = child.wait();
        panic!("Cold start probe returned non-200 status: {}", response_str);
    }

    let _ = child.kill();
    let _ = child.wait();

    duration_micros as f64 / 1000.0
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: bench_cold_start <command_string> <port> [repetitions]");
        std::process::exit(1);
    }

    let cmd_str = &args[1];
    let port: u16 = args[2].parse().expect("Invalid port number");
    let reps: usize = args.get(3).and_then(|s| s.parse().ok()).unwrap_or(1);

    for i in 1..=reps {
        let ms = measure_cold_start(cmd_str, port);
        println!("{:.3}", ms);
        if reps > 1 && i < reps {
            sleep(Duration::from_millis(50));
        }
    }
}
