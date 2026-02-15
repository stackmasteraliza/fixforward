/// Clamps a value between a minimum and maximum.
pub fn clamp(value: i32, min: i32, max: i32) -> i32 {
    if value < min {
        min
    } else if value >= max {  // Bug: should be > not >=
        max
    } else {
        value
    }
}

/// Returns the nth Fibonacci number.
pub fn fibonacci(n: u32) -> u64 {
    if n == 0 {
        return 0;
    }
    if n == 1 {
        return 1;
    }
    let mut a: u64 = 0;
    let mut b: u64 = 1;
    for _ in 2..=n {
        let temp = a + b;
        a = b;
        b = temp;
    }
    b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clamp_within_range() {
        assert_eq!(clamp(5, 1, 10), 5);
    }

    #[test]
    fn test_clamp_at_max() {
        assert_eq!(clamp(10, 1, 10), 10);  // Fails: >= returns 10 but boundary is wrong
    }

    #[test]
    fn test_clamp_below_min() {
        assert_eq!(clamp(0, 1, 10), 1);
    }

    #[test]
    fn test_clamp_above_max() {
        assert_eq!(clamp(15, 1, 10), 10);
    }

    #[test]
    fn test_fibonacci_base() {
        assert_eq!(fibonacci(0), 0);
        assert_eq!(fibonacci(1), 1);
    }

    #[test]
    fn test_fibonacci_sequence() {
        assert_eq!(fibonacci(10), 55);
    }
}
