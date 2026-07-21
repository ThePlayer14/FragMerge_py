"""fragmerge_core.py

Pure-Python reimplementation of asmodean's "merge_*frag" tools
(exlnk4/src/merge_11ecfrag.cpp, merge_11ecfrag2.cpp, merge_5pbfrag.cpp).

Each tool takes one or two source BMPs plus a game-specific binary
"descriptor" (.dat) that maps source tiles/blocks onto a reassembled
output image.  This module does the same with numpy, and exposes a
high-level :func:`merge` that optionally enables/disables individual
fragments (the C tools' "merge index" feature).

No native codecs are involved -- only struct parsing + pixel remapping.

Orientation note
----------------
asmodean's as-util reads BMP rows bottom-up then flips them to top-down
internally, does all the block math in top-down coordinates, then writes
the output BMP flipped back.  We load BMPs top-down via Pillow (row 0 =
top) and write standard BMPs, which is the exact same net result.
"""

from __future__ import annotations

import json
import os
import struct
from collections import defaultdict
from typing import Iterable, Optional, Sequence

import numpy as np
from PIL import Image

__all__ = ["load_rgba", "save_rgba", "merge", "FORMATS",
           "write_extract_sidecar", "read_extract_sidecar",
           "sidecar_sources", "dump_slices", "dump_slices_images",
           "parse_mappings"]


FORMATS = ("chara", "bg", "5pb", "sg")

# Block sizes (square) per format.
_CHARA_BLOCK = 32
_CHARA_DST = _CHARA_BLOCK - 2      # 30 px out: 1px border trimmed each side
_BG_BLOCK = 16
_BG_DST = _BG_BLOCK               # no border trim
_5PB_BLOCK = 32
_SG_BLOCK = 32                     # MAGES sprite chunk size

# Sprite-type nibble (low byte D of the 4-byte sprite info field).
_SG_TYPE_BASE = 0x00
_SG_TYPE_SUB = 0x20
_SG_TYPE_DEP = (0x30, 0x40, 0x60)
_SG_TYPE_OVERLAY = 0x50


# --------------------------------------------------------------------------- #
# Extraction sidecar
# --------------------------------------------------------------------------- #
def write_extract_sidecar(folder: str, idx: int, dat_basename: str,
                           src_idx: int | None = None) -> str:
    """Write a ``file_NNNN.json`` sidecar next to a descriptor ``.bin``.

    Records the descriptor index, filename, and which source PNGs exist
    (both the ``bg`` two-half convention and the single-source convention).
    ``src_idx`` is the index of the source atlas PNG; defaults to ``idx``.
    For ``chara`` the atlas precedes the descriptor, so callers pass
    ``idx - 1``.  The GUI reads this to auto-resolve a merge without naming
    conventions.
    """
    if src_idx is None:
        src_idx = idx
    single = os.path.join(folder, "file_%04d.png" % src_idx)
    bg1 = os.path.join(folder, "file_%04d.png" % (idx - 2))
    bg2 = os.path.join(folder, "file_%04d.png" % (idx - 1))
    # Record the expected source basenames unconditionally. The atlas PNG may
    # not exist yet at sidecar-write time (e.g. it is decoded in a later/parallel
    # pass), so existence is checked by the resolver, not here.
    data = {
        "index": idx,
        "descriptor": dat_basename,
        "sources": {
            "single": [os.path.basename(single)],
            "bg": [os.path.basename(bg1), os.path.basename(bg2)],
        },
    }
    sidecar = os.path.join(folder, "file_%04d.json" % idx)
    with open(sidecar, "w") as f:
        json.dump(data, f, indent=2)
    return sidecar


def read_extract_sidecar(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def sidecar_sources(sc: dict, fmt: str, folder: str) -> list[str]:
    """Resolve the source image paths for ``fmt`` from a sidecar dict."""
    key = "bg" if fmt == "bg" else "single"
    return [os.path.join(folder, s) for s in sc.get("sources", {}).get(key, [])]


# --------------------------------------------------------------------------- #
# Image load / save (alpha-preserving)
# --------------------------------------------------------------------------- #
def _load_bmp_rgba(path: str) -> np.ndarray:
    """Load a 24/32-bit BMP preserving alpha (top-down).

    Pillow's BMP reader silently drops the alpha channel, so asmodean-style
    32-bit RGBA BMPs would lose alpha.  We parse the raw bitmap ourselves.
    Supports BI_RGB, 24/32 bpp, top- or bottom-up orientation.
    """
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"BM":
        raise ValueError("not a BMP file: %s" % path)
    off = int.from_bytes(data[10:14], "little")
    w = int.from_bytes(data[18:22], "little")
    h_raw = int.from_bytes(data[22:26], "little")
    h = abs(h_raw)
    top_down = h_raw < 0
    bpp = int.from_bytes(data[28:30], "little")
    if int.from_bytes(data[30:34], "little") != 0:
        raise ValueError("compressed BMP not supported: %s" % path)
    if bpp not in (24, 32):
        raise ValueError("only 24/32-bit BMP supported, got %d bpp" % bpp)

    row_bytes = ((w * bpp + 31) // 32) * 4
    pix = data[off:off + row_bytes * h]
    if bpp == 32:
        arr = np.frombuffer(pix, dtype=np.uint8).reshape(h, row_bytes)[:, :w * 4]
        out = arr.reshape(h, w, 4)[:, :, (2, 1, 0, 3)].copy()
    else:
        arr = np.frombuffer(pix, dtype=np.uint8).reshape(h, row_bytes)[:, :w * 3]
        out = np.zeros((h, w, 4), dtype=np.uint8)
        out[:, :, :3] = arr.reshape(h, w, 3)[:, :, (2, 1, 0)]
        out[:, :, 3] = 255

    return np.flipud(out) if not top_down else out


def load_rgba(path: str) -> np.ndarray:
    """Load any image as an (H, W, 4) uint8 RGBA array, top-down."""
    if os.path.splitext(path)[1].lower() == ".bmp":
        return _load_bmp_rgba(path)
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def save_rgba(arr: np.ndarray, path: str, flip: bool = False) -> None:
    """Save an (H, W, 4) uint8 array, preserving alpha.

    Format follows ``path`` extension: ``.png`` (default) or ``.bmp``.
    ``flip`` vertically flips first, for parity with the C tools' flip
    when fed bottom-up sources.
    """
    out = np.flipud(arr) if flip else arr
    fmt = "BMP" if os.path.splitext(path)[1].lower() == ".bmp" else "PNG"
    Image.fromarray(np.ascontiguousarray(out, dtype=np.uint8), "RGBA").save(path, fmt)


# --------------------------------------------------------------------------- #
# Descriptor parsing (shared by merge + debug dumps)
# --------------------------------------------------------------------------- #
def _5pb_scale(src_h: Optional[int]) -> int:
    """Source-y atlas scale for 5pb/MAGES descriptors.

    The original C++ tool (merge_5pbfrag.cpp) uses a bucketing heuristic
    based on atlas height: ≤256→256, ≤512→512, ≤1024→1024, else→2048.
    This is WRONG for the Steins;Gate X360 chara.dat 5pb descriptors:
    their src_y floats are normalised to a fixed virtual height of 1024,
    *not* to the actual atlas pixel height.  Using any other scale
    compresses the vertical coordinate into the wrong range, scrambling
    the merged output (verified for 224px and 448px atlases alike).

    Always return 1024 — the C++ heuristic is simply incorrect for this
    format.
    """
    return 1024


def _read_dat(fmt: str, dat: bytes) -> dict:
    """Return a normalized descriptor structure for ``fmt``.

    The parsing logic lives here exactly once; both merging and the debug
    dumps consume this structure.
    """
    if fmt == "chara":
        e1c, e2c, w, h, w2, h2, unk = struct.unpack_from("<6H I", dat, 0)
        entries = []
        off = 16
        for _ in range(e1c):
            u1, u2, e2off, ox, oy, wb, hb = struct.unpack_from("<2H I 4H", dat, off)
            off += 16
            entries.append({"ox": ox, "oy": oy, "wb": wb, "hb": hb, "e2off": e2off})
        return {"entries": entries}

    if fmt == "bg":
        w0, h0 = struct.unpack_from("<2H", dat, 0)
        p = 4
        base = {"ox": 0, "oy": 0, "wb": w0, "hb": h0,
                "pairs_off": p, "pairs_len": w0 * h0}
        count = struct.unpack_from("<H", dat, p + w0 * h0 * 2)[0]
        extras = []
        p2 = p + w0 * h0 * 2 + 2
        for _ in range(count):
            offset = struct.unpack_from("<H", dat, p2)[0] * 4
            p2 += 2
            ox, oy, wb, hb = struct.unpack_from("<4H", dat, offset)
            extras.append({"ox": ox, "oy": oy, "wb": wb, "hb": hb,
                           "pairs_off": offset + 8, "pairs_len": wb * hb})
        return {"base": base, "extras": extras}

    # sg (MAGES / Steins;Gate PC .lay): little-endian, sprite list + chunk list.
    if fmt == "sg":
        sprite_count, chunk_count = struct.unpack_from("<2I", dat, 0)
        off = 8
        sprites = []
        for _ in range(sprite_count):
            a, b, c, d8 = struct.unpack_from("<4B", dat, off)
            chunk_off, chunk_cnt = struct.unpack_from("<2I", dat, off + 4)
            sprites.append({"type": d8, "id": a, "dep_id": b, "sub_id": c,
                            "chunk_off": chunk_off, "chunk_count": chunk_cnt})
            off += 12
        # Chunk list: <2I header already consumed; each chunk is 4 little-endian
        # floats [dst_x, dst_y, src_x, src_y] (16 bytes).  Trailing "junk" (a
        # preview bitmap) follows; ignore it.  src points at pixel [1,1] so the
        # caller subtracts 1; dst points at [0,0] of the target chunk.
        chunk_base = off
        chunks = np.zeros((chunk_count, 4), dtype=np.float64)
        for k in range(chunk_count):
            chunks[k] = struct.unpack_from("<4f", dat, chunk_base + k * 16)
        return {"sprites": sprites, "chunks": chunks}

    # 5pb (5pb / MAGES on Xbox 360, per asmodean's merge_5pbfrag.cpp v1.01):
    #   FRAGHDR   : u32 BE entry1_count, u32 BE entry2_count
    #   FRAGENTRY1: u16 unknown1, u16 unknown2, u32 BE entry2_start,
    #               u32 BE entry2_count   (x entry1_count)
    #   FRAGENTRY2: 4 x float BE [dst_x, dst_y, src_x, src_y]  (x entry2_count)
    # entry2_start is the offset into the FRAGENTRY2 array; all fragments draw
    # from the single atlas passed alongside the descriptor.
    e1c, e2c = struct.unpack_from(">2I", dat, 0)
    entries1 = []
    off = 8
    for _ in range(e1c):
        u1, u2, s, c = struct.unpack_from(">2H 2I", dat, off)
        off += 12
        entries1.append((s, c))
    e2 = np.asarray(struct.unpack_from(">%df" % (4 * e2c), dat, off),
                    dtype=np.float64).reshape(e2c, 4)
    return {"entries1": entries1, "e2": e2}


def _read_pairs(dat: bytes, off: int, count: int) -> list[tuple[int, int]]:
    """Read ``count`` (ex, ey) byte pairs starting at ``off``."""
    return [(dat[off + 2 * i], dat[off + 2 * i + 1]) for i in range(count)]


def parse_mappings(fmt: str, dat: bytes, frag_idx: Optional[int] = None,
                   src_h: Optional[int] = None) -> list[dict]:
    """Return all (dest, src) block mappings from a descriptor.

    Parameters
    ----------
    fmt : "chara" | "bg" | "5pb"
    dat : raw descriptor bytes
    frag_idx : if given, return only that fragment's mappings
    src_h : source height (needed for 5pb src-y scaling)

    Returns a list of dicts with keys dest_x, dest_y, src_x, src_y.
    """
    if fmt == "chara":
        out = []
        for i, e in enumerate(_read_dat(fmt, dat)["entries"]):
            if frag_idx is not None and i != frag_idx:
                continue
            pairs = _read_pairs(dat, e["e2off"], e["wb"] * e["hb"])
            for idx, (ex, ey) in enumerate(pairs):
                if ex == 0xFF and ey == 0xFF:
                    continue
                bx, by = idx % e["wb"], idx // e["wb"]
                out.append({"dest_x": e["ox"] + bx, "dest_y": e["oy"] + by,
                            "src_x": ex, "src_y": ey})
        return out

    if fmt == "bg":
        parsed = _read_dat(fmt, dat)
        frags = [parsed["base"]] + parsed["extras"]
        out = []
        for i, e in enumerate(frags):
            if frag_idx is not None and i != frag_idx:
                continue
            pairs = _read_pairs(dat, e["pairs_off"], e["pairs_len"])
            for idx, (ex, ey) in enumerate(pairs):
                if ex == 0xFF and ey == 0xFF:
                    continue
                bx, by = idx % e["wb"], idx // e["wb"]
                out.append({"dest_x": e["ox"] + bx, "dest_y": e["oy"] + by,
                            "src_x": ex, "src_y": ey})
        return out

    # 5pb: float coords -> integer block coords
    parsed = _read_dat(fmt, dat)
    entries1, e2 = parsed["entries1"], parsed["e2"]
    minx = miny = np.inf
    maxx = maxy = -np.inf
    for s, c in entries1:
        for j in range(c):
            d = e2[s + j]
            minx, miny = min(minx, d[0]), min(miny, d[1])
            maxx, maxy = max(maxx, d[0]), max(maxy, d[1])
    offset_x = max(-minx, 0.0)
    offset_y = max(-miny, 0.0)
    scale = _5pb_scale(src_h)
    out = []
    for i, (s, c) in enumerate(entries1):
        if frag_idx is not None and i != frag_idx:
            continue
        for j in range(c):
            d = e2[s + j]
            dx = int(d[0] + offset_x)
            dy = int(d[1] + offset_y)
            sx = int(d[2] * 2048 - 1) // _5PB_BLOCK
            sy = int(d[3] * scale - 1) // _5PB_BLOCK
            out.append({"dest_x": dx, "dest_y": dy, "src_x": sx, "src_y": sy})
    return out

    # sg: sprite list with a dependence chain; each chunk is a 32x32 block.
    if fmt == "sg":
        parsed = _read_dat("sg", dat)
        sprites, chunks = parsed["sprites"], parsed["chunks"]
        out = []
        for i, s in enumerate(sprites):
            if frag_idx is not None and i != frag_idx:
                continue
            is_overlay = s["type"] == _SG_TYPE_OVERLAY
            for k in range(s["chunk_off"], s["chunk_off"] + s["chunk_count"]):
                d = chunks[k]
                out.append({"dest_x": int(round(d[0])), "dest_y": int(round(d[1])),
                            "src_x": (int(round(d[2])) - 1) // _SG_BLOCK,
                            "src_y": (int(round(d[3])) - 1) // _SG_BLOCK,
                            "overlay": is_overlay})
        return out


# --------------------------------------------------------------------------- #
# merge: chara / bg / 5pb
# --------------------------------------------------------------------------- #
def _build_canvas(max_wb: int, max_hb: int, dst: int) -> np.ndarray:
    """Allocate a zero (transparent) output canvas from block extents."""
    out_w = max(1, max_wb) * dst
    out_h = max(1, max_hb) * dst
    return np.zeros((out_h, out_w, 4), dtype=np.uint8)


def _oob(src: np.ndarray, sx0: int, sy0: int, block: int) -> bool:
    """True if a source block at (sx0, sy0) is outside the source image."""
    return (sy0 >= src.shape[0] or sx0 >= src.shape[1] or
            sy0 + block > src.shape[0] or sx0 + block > src.shape[1])


def _merge_chara(src: np.ndarray, dat: bytes, enabled: Optional[set[int]]) -> tuple[np.ndarray, int]:
    entries = _read_dat("chara", dat)["entries"]

    max_wb = max_hb = 0
    for e in entries:
        if e["wb"] and e["hb"]:
            max_wb = max(max_wb, e["ox"] + e["wb"])
            max_hb = max(max_hb, e["oy"] + e["hb"])
    out = _build_canvas(max_wb, max_hb, _CHARA_DST)

    for i, e in enumerate(entries):
        if enabled is not None and i not in enabled:
            continue
        pairs = _read_pairs(dat, e["e2off"], e["wb"] * e["hb"])
        for idx, (ex, ey) in enumerate(pairs):
            if ex == 0xFF and ey == 0xFF:
                continue
            bx, by = idx % e["wb"], idx // e["wb"]
            src_xb, src_yb = ex * _CHARA_BLOCK, ey * _CHARA_BLOCK
            if _oob(src, src_xb, src_yb, _CHARA_BLOCK):
                continue
            last_x = bx == e["wb"] - 1
            last_y = by == e["hb"] - 1
            span = _CHARA_BLOCK - 2 if last_x else _CHARA_BLOCK - 1
            dst_y0 = (e["oy"] + by) * _CHARA_DST
            dst_x0 = (e["ox"] + bx) * _CHARA_DST
            for yy in range(1, _CHARA_BLOCK):
                if last_y and yy == _CHARA_BLOCK - 1:
                    break
                src_row = src[src_yb + yy, src_xb + 1:src_xb + 1 + span]
                dst_row = out[dst_y0 + (yy - 1), dst_x0:dst_x0 + span]
                if src_row[:, 3].any():
                    _alphablend(dst_row, src_row)
    return out, len(entries)


def _alphablend(dst_row: np.ndarray, src_row: np.ndarray) -> None:
    """Alpha-over composite ``src_row`` onto ``dst_row`` in-place (straight alpha)."""
    sa = src_row[:, 3:4].astype(np.float32) / 255.0
    da = dst_row[:, 3:4].astype(np.float32) / 255.0
    out_a = sa + da * (1.0 - sa)
    safe = np.where(out_a > 0, out_a, 1.0)
    out_rgb = (src_row[:, :3].astype(np.float32) * sa +
               dst_row[:, :3].astype(np.float32) * da * (1.0 - sa)) / safe
    np.copyto(dst_row[:, :3], out_rgb.astype(np.uint8))
    np.copyto(dst_row[:, 3:4], (out_a * 255).astype(np.uint8))


def _alphablend_block(dst_block: np.ndarray, src_block: np.ndarray) -> None:
    """Alpha-over composite ``src_block`` onto ``dst_block`` in-place (straight alpha)."""
    sa = src_block[:, :, 3:4].astype(np.float32) / 255.0
    da = dst_block[:, :, 3:4].astype(np.float32) / 255.0
    out_a = sa + da * (1.0 - sa)
    safe = np.where(out_a > 0, out_a, 1.0)
    out_rgb = (src_block[:, :, :3].astype(np.float32) * sa +
               dst_block[:, :, :3].astype(np.float32) * da * (1.0 - sa)) / safe
    np.copyto(dst_block[:, :, :3], out_rgb.astype(np.uint8))
    np.copyto(dst_block[:, :, 3:4], (out_a * 255).astype(np.uint8))


def _merge_bg(src1: np.ndarray, src2: np.ndarray, dat: bytes,
              enabled: Optional[set[int]]) -> tuple[np.ndarray, int]:
    # The C tool hardcodes src1's width/stride and copies that many columns
    # from both halves (so a wider src2 is silently truncated).  Mirror that.
    w = src1.shape[1]
    if src2.shape[1] != w:
        s2 = np.zeros((src2.shape[0], w, 4), dtype=np.uint8)
        s2[:, :min(w, src2.shape[1])] = src2[:, :min(w, src2.shape[1])]
        src2 = s2
    src = np.vstack([src1, src2])  # top-down: src1 on top, src2 below

    parsed = _read_dat("bg", dat)
    frags = [parsed["base"]] + parsed["extras"]

    max_wb = max_hb = 0
    for e in frags:
        if e["wb"] and e["hb"]:
            max_wb = max(max_wb, e["ox"] + e["wb"])
            max_hb = max(max_hb, e["oy"] + e["hb"])
    out = _build_canvas(max_wb, max_hb, _BG_DST)

    for i, e in enumerate(frags):
        if enabled is not None and i not in enabled:
            continue
        pairs = _read_pairs(dat, e["pairs_off"], e["pairs_len"])
        for idx, (ex, ey) in enumerate(pairs):
            if ex == 0xFF and ey == 0xFF:
                continue
            bx, by = idx % e["wb"], idx // e["wb"]
            sy0, sx0 = ey * _BG_BLOCK, ex * _BG_BLOCK
            dy0, dx0 = (e["oy"] + by) * _BG_DST, (e["ox"] + bx) * _BG_DST
            if _oob(src, sx0, sy0, _BG_BLOCK):
                continue
            src_block = src[sy0:sy0 + _BG_BLOCK, sx0:sx0 + _BG_BLOCK]
            dst_block = out[dy0:dy0 + _BG_BLOCK, dx0:dx0 + _BG_BLOCK]
            _alphablend_block(dst_block, src_block)
    return out, len(frags)


def _merge_5pb(src: np.ndarray, dat: bytes, enabled: Optional[set[int]],
               scale_override: Optional[int] = None) -> tuple[np.ndarray, int]:
    parsed = _read_dat("5pb", dat)
    entries1, e2 = parsed["entries1"], parsed["e2"]

    minx = miny = np.inf
    maxx = maxy = -np.inf
    for s, c in entries1:
        for j in range(c):
            d = e2[s + j]
            minx, miny = min(minx, d[0]), min(miny, d[1])
            maxx, maxy = max(maxx, d[0]), max(maxy, d[1])

    offset_x = max(-minx, 0.0)
    offset_y = max(-miny, 0.0)
    scale = scale_override if scale_override is not None else _5pb_scale(src.shape[0])

    out_w = int(offset_x + maxx + _5PB_BLOCK)
    out_h = int(offset_y + maxy + _5PB_BLOCK)
    out = np.zeros((out_h, out_w, 4), dtype=np.uint8)

    # asmodean's C++ (merge_5pbfrag.cpp) does per-pixel copy:
    #   src_x = float * 2048 - 1   (as float, not truncated yet)
    #   src_y = float * scale - 1   (as float)
    #   for each (x, y) in 32x32 block:
    #     src_pix = src[(unsigned long)(src_y + y)][(unsigned long)(src_x + x)]
    #     dst_pix = out[(unsigned long)(dst_y + y)][(unsigned long)(dst_x + x)]
    #     *dst_pix = *src_pix
    #
    # The (unsigned long) cast of a float truncates toward zero.  When src_y
    # is fractional (e.g. -0.5), this produces a 1-row shift compared to a
    # block slice src[sy:sy+32] where sy=int(src_y).  We must match the C++
    # per-pixel behaviour exactly.
    src_h, src_w = src.shape[:2]
    for i, (s, c) in enumerate(entries1):
        if enabled is not None and i not in enabled:
            continue
        for j in range(c):
            d = e2[s + j]
            dx_f = d[0] + offset_x
            dy_f = d[1] + offset_y
            sx_f = d[2] * 2048 - 1
            sy_f = d[3] * scale - 1

            sy0 = int(sy_f); sx0 = int(sx_f)
            dy0 = int(dy_f); dx0 = int(dx_f)

            # Clamp source rect to atlas bounds
            ssy = max(sy0, 0); ssx = max(sx0, 0)
            sey = min(sy0 + _5PB_BLOCK, src_h); sex = min(sx0 + _5PB_BLOCK, src_w)
            # Corresponding dest rect
            dsy = dy0 + (ssy - sy0); dsx = dx0 + (ssx - sx0)
            dey = dsy + (sey - ssy); dex = dsx + (sex - ssx)
            # Clamp dest rect to output bounds
            csy = max(dsy, 0); csx = max(dsx, 0)
            cey = min(dey, out_h); cex = min(dex, out_w)
            # Adjust source to match
            asy = ssy + (csy - dsy); asx = ssx + (csx - dsx)
            aey = asy + (cey - csy); aex = asx + (cex - csx)

            if asy >= aey or asx >= aex:
                continue

            sb = src[asy:aey, asx:aex]
            db = out[csy:cey, csx:cex]

            if i == 0:
                np.copyto(db, sb)
            else:
                _alphablend_block(db, sb)
    return out, len(entries1)


def _sg_chain(parsed: dict, i: int) -> list[int]:
    """Return the ordered sprite indices to draw for sprite entry ``i``.

    Follows the MAGES dependence chain (spec): ``Dep -> Sub -> Base``, drawn in
    reverse-dependence order (Base first, then Sub, then Dep, then Overlay).
    """
    sprites = parsed["sprites"]
    target = sprites[i]
    order: list[int] = []
    # Base sprite (type 0x00) is always drawn first if present.
    base_idx = next((k for k, s in enumerate(sprites) if s["type"] == _SG_TYPE_BASE), None)
    if base_idx is not None and base_idx != i:
        order.append(base_idx)
    if target["type"] == _SG_TYPE_BASE:
        return [i] if base_idx is None else order + [i]
    if target["type"] == _SG_TYPE_SUB:
        # Sub depends on base.
        return (order + [i]) if base_idx is not None else [i]
    if target["type"] in _SG_TYPE_DEP:
        # Dep depends on the sub whose id == target.dep_id.
        sub_idx = next((k for k, s in enumerate(sprites)
                        if s["type"] == _SG_TYPE_SUB and s["id"] == target["dep_id"]), None)
        if sub_idx is not None:
            order.append(sub_idx)
        return order + [i]
    # Overlay: drawn on top of whatever is present; for an isolated render just
    # itself (it blends via alpha).
    return [i]


def _merge_sg(src: np.ndarray, dat: bytes, enabled: Optional[set[int]]) -> tuple[np.ndarray, int]:
    parsed = _read_dat("sg", dat)
    sprites = parsed["sprites"]
    chunks = parsed["chunks"]

    # Determine which sprite entries to draw and in what order.
    if enabled is None:
        # Draw everything in dependence order: base, subs, deps, overlays.
        draw = list(range(len(sprites)))
    else:
        draw = []
        for i in enabled:
            for k in _sg_chain(parsed, i):
                if k not in draw:
                    draw.append(k)

    # Compute canvas extents over the chunks of the sprites we will draw.
    minx = miny = np.inf
    maxx = maxy = -np.inf
    for i in draw:
        s = sprites[i]
        for k in range(s["chunk_off"], s["chunk_off"] + s["chunk_count"]):
            d = chunks[k]
            minx, miny = min(minx, d[0]), min(miny, d[1])
            maxx, maxy = max(maxx, d[0]), max(maxy, d[1])
    if not np.isfinite(minx):
        return np.zeros((1, 1, 4), dtype=np.uint8), len(sprites)
    off_x = int(round(-minx))
    off_y = int(round(-miny))
    out_w = int(round(maxx - minx)) + _SG_BLOCK
    out_h = int(round(maxy - miny)) + _SG_BLOCK
    out = np.zeros((out_h, out_w, 4), dtype=np.uint8)

    for i in draw:
        s = sprites[i]
        is_overlay = s["type"] == _SG_TYPE_OVERLAY
        for k in range(s["chunk_off"], s["chunk_off"] + s["chunk_count"]):
            d = chunks[k]
            dx = int(round(d[0])) + off_x
            dy = int(round(d[1])) + off_y
            sx = int(round(d[2])) - 1
            sy = int(round(d[3])) - 1
            if _oob(src, sx, sy, _SG_BLOCK):
                continue
            block = src[sy:sy + _SG_BLOCK, sx:sx + _SG_BLOCK]
            if is_overlay:
                dst = out[dy:dy + _SG_BLOCK, dx:dx + _SG_BLOCK]
                a = block[:, :, 3:4].astype(np.float32) / 255.0
                out[dy:dy + _SG_BLOCK, dx:dx + _SG_BLOCK] = (
                    (block[:, :, :3].astype(np.float32) * a
                     + dst[:, :, :3].astype(np.float32) * (1 - a))
                ).astype(np.uint8)
                out[dy:dy + _SG_BLOCK, dx:dx + _SG_BLOCK, 3] = np.maximum(
                    dst[:, :, 3], block[:, :, 3])
            else:
                out[dy:dy + _SG_BLOCK, dx:dx + _SG_BLOCK] = block
    return out, len(sprites)


def merge(fmt: str,
          src_paths: Sequence[str],
          dat_path: str,
          enabled: Optional[Iterable[int]] = None,
          scale_override: Optional[int] = None) -> tuple[np.ndarray, int]:
    """Reassemble a sliced image.

    Parameters
    ----------
    fmt : one of ``"chara"``, ``"bg"``, ``"5pb"``, ``"sg"``.
    src_paths : source image path(s).  chara/5pb use one; bg uses two.
    dat_path : path to the descriptor ``.dat``.
    enabled : iterable of fragment indexes to include.  ``None`` = all.
    scale_override : for ``5pb`` only, force the source-y atlas scale.

    Returns (out_array, fragment_count).
    """
    if fmt not in FORMATS:
        raise ValueError("fmt must be one of %s" % (FORMATS,))
    with open(dat_path, "rb") as f:
        dat = f.read()
    en = None if enabled is None else set(enabled)

    if fmt == "chara":
        return _merge_chara(load_rgba(src_paths[0]), dat, en)
    if fmt == "bg":
        return _merge_bg(load_rgba(src_paths[0]), load_rgba(src_paths[1]), dat, en)
    if fmt == "sg":
        return _merge_sg(load_rgba(src_paths[0]), dat, en)
    return _merge_5pb(load_rgba(src_paths[0]), dat, en, scale_override)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("usage: fragmerge_core.py <chara|bg|5pb> <src1> [<src2>] <desc.dat> [out]")
        raise SystemExit(1)
    fmt = sys.argv[1]
    if fmt == "bg":
        srcs = [sys.argv[2], sys.argv[3]]
        dat = sys.argv[4]
        out = sys.argv[5] if len(sys.argv) > 5 else "out.bmp"
    else:
        srcs = [sys.argv[2]]
        dat = sys.argv[3]
        out = sys.argv[4] if len(sys.argv) > 4 else "out.bmp"
    arr, n = merge(fmt, srcs, dat)
    save_rgba(arr, out)
    print("merged %d fragments -> %s (%dx%d)" % (n, out, arr.shape[1], arr.shape[0]))


# --------------------------------------------------------------------------- #
# Debug: text grid / fragment list
# --------------------------------------------------------------------------- #
def dump_slices(fmt: str, dat_path: str, out_path: str | None = None) -> str:
    """Dump the slice reassembly mapping as text.

    For ``chara`` / ``bg``: a 2D grid of destination blocks; each cell is the
    source (ex, ey); ``..`` means skip (0xFF,0xFF).
    For ``5pb``: a per-fragment list of float coordinates (not grid-aligned).
    """
    with open(dat_path, "rb") as f:
        dat = f.read()

    if fmt == "5pb":
        lines = _dump_5pb_list(dat)
    elif fmt == "sg":
        lines = _dump_sg_list(dat)
    else:
        lines = _format_grid(fmt, dat)

    header = "format: %s   descriptor: %s\n" % (fmt, dat_path)
    if fmt in ("chara", "bg"):
        header += ("dest block grid (rows = dest y, cols = dest x); "
                   "cell = source (ex,ey); '..' = skip (0xFF,0xFF)\n")
    text = header + "\n".join(lines)
    if out_path:
        with open(out_path, "w") as f:
            f.write(text)
    return text


def _format_grid(fmt: str, dat: bytes) -> list[str]:
    """Build the chara/bg destination grid text from the descriptor."""
    mappings = parse_mappings(fmt, dat)
    cells = {}
    max_dx = max_dy = 0
    for m in mappings:
        max_dx = max(max_dx, m["dest_x"])
        max_dy = max(max_dy, m["dest_y"])
        cells[(m["dest_x"], m["dest_y"])] = (m["src_x"], m["src_y"])

    lines = []
    for dy in range(max_dy + 1):
        row = []
        for dx in range(max_dx + 1):
            c = cells.get((dx, dy))
            row.append("  .. " if c is None else "%2d,%02d" % c)
        lines.append(" ".join(row))
    return lines


def _dump_5pb_list(dat: bytes) -> list[str]:
    entries1, e2 = _read_dat("5pb", dat)["entries1"], _read_dat("5pb", dat)["e2"]
    lines = ["5pb descriptor (float coords): frag_index | dst_x dst_y | src_x src_y (raw)"]
    for i, (s, c) in enumerate(entries1):
        lines.append("  frag %d (%d blocks):" % (i, c))
        for j in range(c):
            d = e2[s + j]
            lines.append("    block %2d: dst=(%.2f, %.2f)  src=(%.2f, %.2f)"
                         % (j, d[0], d[1], d[2], d[3]))
    return lines


_SG_TYPE_NAMES = {_SG_TYPE_BASE: "base", _SG_TYPE_SUB: "sub",
                  _SG_TYPE_OVERLAY: "overlay"}
_SG_TYPE_NAMES.update({t: "dep" for t in _SG_TYPE_DEP})


def _dump_sg_list(dat: bytes) -> list[str]:
    parsed = _read_dat("sg", dat)
    lines = ["sg descriptor (MAGES .lay): sprite_index | type id dep_id | chunk_off chunk_count"]
    for i, s in enumerate(parsed["sprites"]):
        tname = _SG_TYPE_NAMES.get(s["type"], "0x%02x" % s["type"])
        lines.append("  sprite %2d: %-7s id=%-3d dep=%-3d chunks[%d..%d) (%d blocks)"
                     % (i, tname, s["id"], s["dep_id"],
                        s["chunk_off"], s["chunk_off"] + s["chunk_count"], s["chunk_count"]))
    return lines


# --------------------------------------------------------------------------- #
# Debug: horizontal slice strips (one per source row run)
# --------------------------------------------------------------------------- #
def dump_slices_images(fmt: str,
                       src_paths: Sequence[str],
                       dat_path: str,
                       out_dir: str,
                       prefix: str = "slice",
                       frag_idx: int | None = None) -> dict:
    """Extract horizontal strips from the source image(s).

    A "strip" is a consecutive run of source blocks on the same source row,
    as referenced by the descriptor (optionally a single fragment).  Each
    strip is saved as a PNG and recorded in ``manifest.json`` together with
    the destination placement of every block.

    Returns {"strips": [...], "manifest_path": ...}.
    """
    os.makedirs(out_dir, exist_ok=True)
    with open(dat_path, "rb") as f:
        dat = f.read()

    # Load source(s) the same way merge() does.
    if fmt == "bg":
        src1 = load_rgba(src_paths[0])
        src2 = load_rgba(src_paths[1])
        w = src1.shape[1]
        if src2.shape[1] != w:
            s2 = np.zeros((src2.shape[0], w, 4), dtype=np.uint8)
            s2[:, :min(w, src2.shape[1])] = src2[:, :min(w, src2.shape[1])]
            src2 = s2
        src = np.vstack([src1, src2])
    else:
        src = load_rgba(src_paths[0])
    src_h = src.shape[0]

    mappings = parse_mappings(fmt, dat, frag_idx, src_h)
    block = (_CHARA_BLOCK if fmt == "chara"
             else _BG_BLOCK if fmt == "bg"
             else _SG_BLOCK if fmt == "sg"
             else _5PB_BLOCK)

    # Group by source row, find consecutive src_x runs -> strips.
    by_row: dict[int, list[int]] = defaultdict(list)
    for m in mappings:
        by_row[m["src_y"]].append(m["src_x"])

    strips = []
    strip_index = {}  # (src_y, start_ex, length) -> strip index
    for src_y, xs in by_row.items():
        xs = sorted(set(xs))
        i = 0
        while i < len(xs):
            start_ex = xs[i]
            length = 1
            while i + length < len(xs) and xs[i + length] == start_ex + length:
                length += 1
            key = (src_y, start_ex, length)
            if key not in strip_index:
                strip_index[key] = len(strips)
                sy, sx = src_y * block, start_ex * block
                ex = min(sx + length * block, src.shape[1])
                ey = min(sy + block, src_h)
                if sx >= src.shape[1] or sy >= src_h:
                    strip = np.zeros((block, block * length, 4), dtype=np.uint8)
                    oob = True
                else:
                    strip = src[sy:ey, sx:ex].copy()
                    oob = (ex - sx) < length * block or (ey - sy) < block
                name = "%s_%04d_sy%03d_ex%03d_len%03d.png" % (
                    prefix, len(strips), src_y, start_ex, length)
                save_rgba(strip, os.path.join(out_dir, name))
                strips.append({
                    "file": name, "src_y": src_y, "start_ex": start_ex,
                    "length": length, "block_w": block, "block_h": block,
                    "actual_w": ex - sx, "actual_h": ey - sy, "out_of_bounds": oob,
                })
            i += length

    # Build manifest: each mapping -> strip file + offset within strip.
    placements = []
    for m in mappings:
        for idx, strip in enumerate(strips):
            if (strip["src_y"] == m["src_y"]
                    and strip["start_ex"] <= m["src_x"] < strip["start_ex"] + strip["length"]):
                placements.append({
                    "dest_x": m["dest_x"], "dest_y": m["dest_y"],
                    "strip_index": idx, "strip_file": strip["file"],
                    "offset_in_strip": m["src_x"] - strip["start_ex"],
                })
                break

    manifest = {
        "format": fmt,
        "descriptor": os.path.basename(dat_path),
        "fragment_index": frag_idx,
        "block_size": [block, block],
        "source_images": [os.path.basename(p) for p in src_paths],
        "strips": strips,
        "placements": placements,
    }
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return {"strips": strips, "manifest_path": manifest_path}


# --------------------------------------------------------------------------- #
# Debug: per-fragment reconstruction
# --------------------------------------------------------------------------- #
def descriptor_frag_count(fmt: str, dat: bytes) -> int:
    """Number of fragments described by a descriptor blob."""
    if fmt == "bg":
        w0, h0 = struct.unpack_from("<2H", dat, 0)
        p = 4 + w0 * h0 * 2
        return 1 + struct.unpack_from("<H", dat, p)[0]
    if fmt == "chara":
        return struct.unpack_from("<6H I", dat, 0)[0]
    if fmt == "sg":
        return struct.unpack_from("<2I", dat, 0)[0]
    return struct.unpack_from(">2I", dat, 0)[0]


def reconstruct_fragments(fmt: str,
                          src_paths: Sequence[str],
                          dat_path: str,
                          out_dir: str,
                          prefix: str = "frag",
                          scale_override: Optional[int] = None) -> dict:
    """Reconstruct each fragment of a descriptor into its own destination canvas.

    For every fragment index ``fi`` (0..count-1), render only that fragment
    (``merge(..., enabled={fi})``) and save it as
    ``<out_dir>/file_NNNN/file_NNNN_frag_MMM/<prefix>_MMM.png`` — the same
    folder layout ``dump_slices_images`` uses per fragment, so the two debug
    outputs sit side by side.

    Returns {"descriptor": ..., "fragment_count": ..., "images": [...],
    "manifest_path": ...}.
    """
    with open(dat_path, "rb") as f:
        dat = f.read()
    frag_count = descriptor_frag_count(fmt, dat)
    base = os.path.splitext(os.path.basename(dat_path))[0]

    images = []
    for fi in range(frag_count):
        arr, _ = merge(fmt, src_paths, dat_path, enabled={fi},
                       scale_override=scale_override)
        frag_dir = os.path.join(out_dir, base, "%s_frag_%03d" % (base, fi))
        os.makedirs(frag_dir, exist_ok=True)
        name = "%s_%03d.png" % (prefix, fi)
        save_rgba(arr, os.path.join(frag_dir, name))
        images.append({
            "fragment_index": fi,
            "file": name,
            "width": arr.shape[1],
            "height": arr.shape[0],
        })

    manifest = {
        "format": fmt,
        "descriptor": os.path.basename(dat_path),
        "fragment_count": frag_count,
        "prefix": prefix,
        "images": images,
    }
    manifest_path = os.path.join(out_dir, base, "reconstruct_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return {"descriptor": os.path.basename(dat_path),
            "fragment_count": frag_count, "images": images,
            "manifest_path": manifest_path}
