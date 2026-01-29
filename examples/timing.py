#!/usr/bin/env python3
"""
Benchmark: uint8 -> float32 vs uint32 -> float32

Creates two arrays with the same number of elements:
  1) uint8
  2) uint32
Converts each to float32 using NumPy and benchmarks speed + rough bandwidth.

Notes:
- This measures conversion + memory traffic. On modern CPUs this is usually memory-bandwidth limited.
- We include a warm-up and repeat multiple times, reporting best/median.
"""

from __future__ import annotations

import time
import statistics as stats
import numpy as np


def bench_convert(arr: np.ndarray, repeats: int = 20) -> dict:
    """Benchmark arr.astype(np.float32, copy=False) across repeats."""
    # Warm-up (prime caches/JIT paths, allocate any internal stuff)
    out = arr.astype(np.float32, copy=False)
    _ = float(out.sum())  # touch output so it can't be trivially skipped

    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = arr.astype(np.float32, copy=False)
        # Touch output to ensure the work happened (prevents dead-code elimination vibes)
        _ = float(out.sum())
        t1 = time.perf_counter()
        times.append(t1 - t0)

    n = arr.size
    in_bytes = arr.nbytes
    out_bytes = n * np.dtype(np.float32).itemsize
    total_bytes = in_bytes + out_bytes  # simple read+write estimate

    best = min(times)
    median = stats.median(times)

    return {
        "n_elems": n,
        "in_dtype": str(arr.dtype),
        "in_bytes": in_bytes,
        "out_bytes": out_bytes,
        "total_bytes_est": total_bytes,
        "best_s": best,
        "median_s": median,
        "best_GBps_est": (total_bytes / best) / 1e9,
        "median_GBps_est": (total_bytes / median) / 1e9,
        "times_s": times,
    }


def format_result(r: dict) -> str:
    return (
        f"dtype {r['in_dtype']:>5} -> float32 | "
        f"N={r['n_elems']:,} | "
        f"best={r['best_s']*1e3:8.3f} ms | "
        f"median={r['median_s']*1e3:8.3f} ms | "
        f"best BW~{r['best_GBps_est']:6.2f} GB/s | "
        f"median BW~{r['median_GBps_est']:6.2f} GB/s"
    )


def main():
    # ---- Parameters you can tweak ----
    n_elems = 20_000_000   # 20 million elements; big enough to be meaningful
    repeats = 15           # repeats for timing
    seed = 123             # RNG seed for reproducibility
    # ----------------------------------

    rng = np.random.default_rng(seed)

    # Create arrays with same number of elements
    a_u8 = rng.integers(0, 256, size=n_elems, dtype=np.uint8)
    a_u32 = rng.integers(0, 2**32, size=n_elems, dtype=np.uint32)

    print("Benchmarking NumPy conversions to float32...\n")
    r_u8 = bench_convert(a_u8, repeats=repeats)
    r_u32 = bench_convert(a_u32, repeats=repeats)

    print(format_result(r_u8))
    print(format_result(r_u32))
    print()

    # Decide "faster" by median time (more stable than best)
    faster = "uint8 -> float32" if r_u8["median_s"] < r_u32["median_s"] else "uint32 -> float32"
    speedup = (r_u32["median_s"] / r_u8["median_s"]) if faster == "uint8 -> float32" else (r_u8["median_s"] / r_u32["median_s"])

    print(f"Winner (by median time): {faster}")
    print(f"Speed ratio (loser/ winner): {speedup:.3f}×")

    # Extra: show estimated memory traffic differences
    print("\nEstimated memory traffic per conversion:")
    print(f"  uint8  input bytes: {r_u8['in_bytes']:,}  | total (in+out): {r_u8['total_bytes_est']:,}")
    print(f"  uint32 input bytes: {r_u32['in_bytes']:,} | total (in+out): {r_u32['total_bytes_est']:,}")

    print(
        "\nInterpretation tip: uint8 reads 1 byte/element, uint32 reads 4 bytes/element, "
        "but both write 4 bytes/element (float32). So uint32->float32 generally pushes "
        "more bytes through memory and often ends up slower when bandwidth-limited."
    )


if __name__ == "__main__":
    main()
