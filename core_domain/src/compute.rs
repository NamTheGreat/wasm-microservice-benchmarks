/// Iterative Fibonacci — wrapped in `black_box` to prevent compiler const-folding.
///
/// Returns the nth Fibonacci number (0-indexed: fib(0)=0, fib(1)=1, …).
/// Uses `std::hint::black_box` on every iteration result to prevent the
/// compiler from constant-folding the entire computation away.
pub fn fibonacci(n: u64) -> u64 {
    if n == 0 {
        return std::hint::black_box(0);
    }
    if n == 1 {
        return std::hint::black_box(1);
    }

    let mut a: u64 = 0;
    let mut b: u64 = 1;
    for _ in 2..=n {
        let next = std::hint::black_box(a.wrapping_add(b));
        a = std::hint::black_box(b);
        b = next;
    }
    std::hint::black_box(b)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fibonacci_sequence() {
        assert_eq!(fibonacci(0), 0);
        assert_eq!(fibonacci(1), 1);
        assert_eq!(fibonacci(2), 1);
        assert_eq!(fibonacci(3), 2);
        assert_eq!(fibonacci(10), 55);
        assert_eq!(fibonacci(20), 6765);
    }
}
