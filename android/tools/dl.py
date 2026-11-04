#!/usr/bin/env python3
"""Robust parallel-range downloader for a very slow HTTPS host.

chaquo.com serves at ~1 KB/s per connection and stalls after ~30-40 KB, so we
pull the file in small byte ranges over many connections and stitch the parts.
"""
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

CHUNK = int(os.environ.get("DL_CHUNK", 48 * 1024))
PARALLEL = int(os.environ.get("DL_PARALLEL", 20))
MAX_TIME = int(os.environ.get("DL_TIMEOUT", 40))


def remote_size(url: str) -> int:
    for _ in range(5):
        p = subprocess.run(
            ["curl", "-sS", "-I", "--max-time", "30", url],
            capture_output=True, text=True,
        )
        for line in p.stdout.splitlines():
            if line.lower().startswith("content-length:"):
                return int(line.split(":", 1)[1].strip())
    raise SystemExit(f"cannot get size of {url}")


def fetch_chunk(url: str, start: int, end: int, out: str, idx: int) -> None:
    """Download bytes [start, end] appending to out/idx.part, retrying stalls."""
    part = os.path.join(out, f"{idx:05d}.part")
    got = 0
    total = end - start + 1
    attempts = 0
    with open(part, "wb") as fh:
        while got < total:
            attempts += 1
            if attempts > 40:
                raise SystemExit(f"chunk {idx}: too many retries")
            lo = start + got
            tmp = part + ".tmp"
            subprocess.run(
                ["curl", "-sS", "--max-time", str(MAX_TIME), "--range", f"{lo}-{end}",
                 "-o", tmp, url],
                capture_output=True,
            )
            if os.path.exists(tmp):
                with open(tmp, "rb") as src:
                    data = src.read()
                os.unlink(tmp)
                if data:
                    fh.write(data)
                    fh.flush()
                    got += len(data)


def download(url: str, dest: str) -> None:
    size = remote_size(url)
    dest_tmp = dest + ".tmpdir"
    os.makedirs(dest_tmp, exist_ok=True)
    ranges = []
    idx = 0
    s = 0
    while s < size:
        e = min(s + CHUNK - 1, size - 1)
        ranges.append((idx, s, e))
        idx += 1
        s = e + 1
    print(f"{os.path.basename(dest)}: {size} bytes in {len(ranges)} chunks", flush=True)
    with ThreadPoolExecutor(PARALLEL) as ex:
        list(ex.map(lambda r: fetch_chunk(url, r[1], r[2], dest_tmp, r[0]), ranges))
    with open(dest, "wb") as out:
        for i in range(len(ranges)):
            with open(os.path.join(dest_tmp, f"{i:05d}.part"), "rb") as fh:
                out.write(fh.read())
    for i in range(len(ranges)):
        os.unlink(os.path.join(dest_tmp, f"{i:05d}.part"))
    os.rmdir(dest_tmp)
    assert os.path.getsize(dest) == size, (os.path.getsize(dest), size)
    print(f"{os.path.basename(dest)}: done", flush=True)


if __name__ == "__main__":
    download(sys.argv[1], sys.argv[2])
