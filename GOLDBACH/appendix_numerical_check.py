"""附录 A：哥德巴赫性质的数值验证。

对 4 <= n <= LIMIT 的每个偶数 n，验证存在素数 p <= n/2，
使得 n - p 也是素数。本程序只使用 Python 标准库，作为定理 4.1
中有限情形核验的补充证据。
"""

LIMIT = 2_000_000


def sieve(limit: int) -> bytearray:
    """返回 is_prime，其中 is_prime[i] == 1 当且仅当 i 为素数。"""
    is_prime = bytearray(b"\x01") * (limit + 1)
    if limit >= 0:
        is_prime[0] = 0
    if limit >= 1:
        is_prime[1] = 0
    i = 2
    while i * i <= limit:
        if is_prime[i]:
            start = i * i
            is_prime[start::i] = bytearray(len(range(start, limit + 1, i)))
        i += 1
    return is_prime


def decompose(n: int, is_prime: bytearray, primes) -> tuple:
    """返回 n 的一个素数分解 (p, n-p)，不存在时返回 None。"""
    for p in primes:
        if p > n // 2:
            break
        if is_prime[n - p]:
            return p, n - p
    return None


def main() -> None:
    is_prime = sieve(LIMIT)
    primes = [i for i in range(2, LIMIT + 1) if is_prime[i]]
    failures = []
    for n in range(4, LIMIT + 1, 2):
        if decompose(n, is_prime, primes) is None:
            failures.append(n)
    print("limit =", LIMIT)
    print("even_numbers_checked =", LIMIT // 2 - 1)
    print("failures =", len(failures))
    print("sample 100 =", decompose(100, is_prime, primes))
    print("sample 1000000 =", decompose(1_000_000, is_prime, primes))


if __name__ == "__main__":
    main()
