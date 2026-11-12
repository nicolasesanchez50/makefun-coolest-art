#!/usr/bin/env python3
"""coolest-art-01 entry: writes the finished picture to the run's output.

The picture is the 1024x1024 PNG committed beside this program as art.png.  The
program checks that the file is a whole, well-formed PNG inside the
competition's limits (<= 1 MiB, <= 1024 px a side) and then copies its bytes to
/output/entry.png unchanged, so the judge sees exactly the file the repository
holds and two runs write identical bytes.

tools/generate.py is the program that drew art.png; it is kept in the repository
so the picture can be reproduced from scratch.

Run:  python3 main.py        (MAKEFUN_OUTPUT_DIR overrides /output locally)
"""

import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = HERE / "art.png"

MAX_BYTES = 1024 * 1024
MAX_SIDE = 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def output_dir() -> Path:
    """The writable directory the harness gives the run (/output by default)."""
    return Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")


def read_png(path: Path) -> bytes:
    """Return the file's bytes, refusing anything that is not a PNG."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"{path.name}: cannot be read ({exc})")
    if not data.startswith(PNG_MAGIC):
        raise SystemExit(f"{path.name}: not a PNG (bad signature)")
    return data


def image_size(data: bytes) -> tuple[int, int]:
    """Width and height from the IHDR chunk, which every PNG header holds."""
    if len(data) < 24 or data[12:16] != b"IHDR":
        raise SystemExit("art.png: no IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def check_whole(data: bytes) -> None:
    """Walk every chunk, verify its CRC, and require a final IEND.

    A truncated or corrupted PNG is refused here rather than by the gate, so a
    broken file never reaches the judge as a blank entry.
    """
    import binascii

    pos = len(PNG_MAGIC)
    seen_iend = False
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        crc = data[pos + 8 + length:pos + 12 + length]
        if len(crc) != 4:
            raise SystemExit("art.png: a chunk is cut short")
        want = binascii.crc32(kind + body) & 0xFFFFFFFF
        if want != struct.unpack(">I", crc)[0]:
            raise SystemExit(f"art.png: chunk {kind!r} fails its checksum")
        pos += 12 + length
        if kind == b"IEND":
            seen_iend = True
            break
    if not seen_iend or pos != len(data):
        raise SystemExit("art.png: the image is not whole")


def main() -> int:
    data = read_png(IMAGE)
    if len(data) > MAX_BYTES:
        raise SystemExit(f"art.png: {len(data)} bytes, over the {MAX_BYTES}-byte limit")
    width, height = image_size(data)
    if width > MAX_SIDE or height > MAX_SIDE:
        raise SystemExit(f"art.png: {width}x{height}, over {MAX_SIDE}px a side")
    check_whole(data)

    out = output_dir()
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SystemExit(f"{out}: cannot be created ({exc})")
    target = out / "entry.png"
    target.write_bytes(data)

    written = target.read_bytes()
    if written != data:
        raise SystemExit("entry.png: what was written is not what was read")
    print(f"wrote {target} ({width}x{height}, {len(data)} bytes)")
    if "--verify" in sys.argv:
        print(f"sha256 {__import__('hashlib').sha256(data).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
