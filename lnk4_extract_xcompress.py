"""lnk4_extract_xcompress.py

Cross-platform extractor for "11eyes CrossOver" and 5pb / MAGES LNK4 containers.

This is a variant of ``lnk4_extract.py`` that decodes the LZXNATIVE blobs with the
real Microsoft ``xcompress.dll`` (via ctypes) instead of the managed libmsxca
reimplementation. It calls ``XMemCreateDecompressionContext`` / ``XMemDecompress``
exactly like asmodean's exlnk4.cpp DecompressData, so it decodes every member that
``xbdecompress.exe`` would -- including ones where libmsxca hits a libmspack edge
case (which previously had to be skipped with a warning).

This module is intended to run on a Windows host where ``xcompress.dll`` (x64) is
loadable via ctypes.WinDLL. Place the DLL next to this script, or anywhere on the
DLL search path.

Output layout mirrors crosslnk4 / lnk4_extract.py exactly: each container member
becomes ``file_NNNN.png`` (when it decodes to a TIMG image) or ``file_NNNN.bin``
(otherwise, e.g. the merge descriptors).

Usage::

    python3 lnk4_extract_xcompress.py <input.lnk4> [output_dir]
"""

from __future__ import annotations

import ctypes
import glob
import os
import struct
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

import fragmerge_core

DEFAULT_WORKERS = os.cpu_count() or 4


def _resolve_sources(fmt: str, extract_dir: str, idx: int) -> list[str] | None:
    """Resolve source PNG paths for a descriptor of `fmt` at member index `idx`.

    chara: atlas is the preceding member (idx-1).  bg: two halves (idx-2, idx-1).
    5pb: same index.  Returns None if any required source is missing.
    """
    if fmt == "bg":
        s1 = os.path.join(extract_dir, "file_%04d.png" % (idx - 2))
        s2 = os.path.join(extract_dir, "file_%04d.png" % (idx - 1))
        if not (os.path.exists(s1) and os.path.exists(s2)):
            return None
        return [s1, s2]
    s1 = os.path.join(extract_dir, "file_%04d.png" % (idx - 1 if fmt == "chara" else idx))
    return [s1] if os.path.exists(s1) else None

# --- locate xcompress.dll --------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_DLL_CANDIDATES = [
    os.path.join(_HERE, "xcompress.dll"),
    os.path.join(_HERE, "..", "xcompress_test", "bin", "libs", "xcompress.dll"),
    "./libs/xcompress.dll",
]

_DLL_PATH = next((os.path.abspath(c) for c in _DLL_CANDIDATES if os.path.exists(c)), None)
if _DLL_PATH is None:
    raise RuntimeError(
        "xcompress.dll not found. Place an x64 xcompress.dll next to this script "
        "or under xcompress_test/bin/MSVC/.")

_xc = ctypes.WinDLL(_DLL_PATH)

XMEMCODEC_LZX = 1

_xc.XMemCreateDecompressionContext.argtypes = [
    ctypes.c_int,            # XMEMCODEC_TYPE CodecType
    ctypes.c_void_p,         # CONST VOID* pCodecParams
    ctypes.c_uint32,         # DWORD Flags
    ctypes.POINTER(ctypes.c_void_p),  # XMEMDECOMPRESSION_CONTEXT* pContext
]
_xc.XMemCreateDecompressionContext.restype = ctypes.c_int  # HRESULT (S_OK == 0)

_xc.XMemDecompress.argtypes = [
    ctypes.c_void_p,         # XMEMDECOMPRESSION_CONTEXT Context
    ctypes.c_void_p,         # VOID* pDestination
    ctypes.POINTER(ctypes.c_size_t),  # SIZE_T* pDestSize (in/out)
    ctypes.c_void_p,         # CONST VOID* pSource
    ctypes.c_size_t,         # SIZE_T SrcSize
]
_xc.XMemDecompress.restype = ctypes.c_int

_xc.XMemDestroyDecompressionContext.argtypes = [ctypes.c_void_p]
_xc.XMemDestroyDecompressionContext.restype = None


def xcompress_decompress(blob: bytes) -> bytes:
    """Decode a single MS-XCA LZXNATIVE blob using xcompress.dll.

    Mirrors exlnk4.cpp: the header's multi-byte fields are stored big-endian on
    disk and are byte-swapped before being passed to the codec. Blocks are
    decoded in sequence with the same context (no reset between blocks)."""
    context_flags = struct.unpack_from(">I", blob, 8)[0]
    flags, window, part = struct.unpack_from(">III", blob, 12)
    unc_low = struct.unpack_from(">I", blob, 28)[0]

    ctx = ctypes.c_void_p()
    codec_params = (ctypes.c_uint32 * 3)(flags, window, part)
    hr = _xc.XMemCreateDecompressionContext(
        XMEMCODEC_LZX, ctypes.byref(codec_params), context_flags, ctypes.byref(ctx))
    if hr != 0:
        raise RuntimeError("XMemCreateDecompressionContext failed, hr 0x%08X" % hr)

    out = bytearray(unc_low)
    out_len = 0
    p = 48
    try:
        while out_len != unc_low:
            block_len = struct.unpack_from(">I", blob, p)[0]
            p += 4
            got = ctypes.c_size_t(unc_low)
            hr = _xc.XMemDecompress(
                ctx,
                ctypes.cast(ctypes.addressof(
                    ctypes.c_char.from_buffer(out)) + out_len, ctypes.c_void_p),
                ctypes.byref(got),
                ctypes.c_char_p(blob[p:p + block_len]), block_len)
            out_len += got.value
            p += block_len
            if hr != 0:
                raise RuntimeError("XMemDecompress failed, hr 0x%08X" % hr)
    finally:
        _xc.XMemDestroyDecompressionContext(ctx)
    return bytes(out[:out_len])


XCOMPRESS_MAGIC = 0x0FF512EE  # big-endian in file
PNG_MAGIC = 0x89504E47         # big-endian in file ("PNG")


# --- TIMG -> PNG (from crosslnk4/lib/timg.py) -------------------------------
def _timg_is_image(data: bytes) -> bool:
    if len(data) < 6:
        return False
    _, _, depth = struct.unpack_from("<HHH", data, 0)
    return depth != 0


def _timg_to_png(data: bytes, png_path: str) -> None:
    """Decode a TIMG blob to PNG.

    The Xbox 360 TIMG atlases store **straight** (non-premultiplied) RGBA — the
    RGB is the true colour and alpha is separate coverage. Write it through
    unchanged; do NOT divide RGB by alpha (that inflates semi-transparent edge
    pixels and clips them to white)."""
    width, height, depth = struct.unpack_from("<HHH", data, 0)
    raw = data[8:]
    if depth == 32 or depth == 0:
        img = Image.frombuffer("RGBA", (width, height), raw, "raw", "ARGB")
    elif depth == 8:
        img = Image.frombuffer("L", (width, height), raw, "raw")
    else:
        img = Image.frombuffer("RGBA", (width, height), raw, "raw", "ARGB")
    img.save(png_path)


# --- LNK4 container ---------------------------------------------------------
def _decode_lzx(member: bytes) -> bytes:
    """Decode a single LZXNATIVE blob via xcompress.dll."""
    return xcompress_decompress(member)


def _write_decoded(out_dir: str, fid: int, dec: bytes, src_idx: int) -> None:
    """Write a decoded LZXNATIVE member, choosing PNG vs .bin by TIMG magic."""
    name = "file_%04d" % fid
    if _timg_is_image(dec):
        _timg_to_png(dec, os.path.join(out_dir, name + ".png"))
    else:
        with open(os.path.join(out_dir, name + ".bin"), "wb") as o:
            o.write(dec)
        fragmerge_core.write_extract_sidecar(
            out_dir, fid, name + ".bin", src_idx=src_idx)


def extract_lnk4(path: str, out_dir: str, workers: int | None = None) -> int:
    with open(path, "rb") as f:
        data = f.read()

    if data[:4] != b"LNK4":
        raise ValueError("%s is not an LNK4 container" % path)

    data_offset = struct.unpack_from("<I", data, 4)[0]
    base = os.path.splitext(os.path.basename(path))[0]

    os.makedirs(out_dir, exist_ok=True)

    workers = workers or DEFAULT_WORKERS

    # First pass (main thread, in member order): classify every member and
    # track `last_png_idx` so each descriptor knows its atlas.  Raw members are
    # written here (cheap copy).  LZXNATIVE members become decode jobs whose
    # `src_idx` is snapshotted now, so the pool can run them out of order.
    jobs: list[tuple[int, bytes, int]] = []  # (fid, member, src_idx)
    count = 0
    offset = 8
    fid = 0
    last_png_idx = -1  # index of the most recent atlas PNG (chara source)
    while True:
        start_blocks = struct.unpack_from("<I", data, offset)[0]
        length_blocks = struct.unpack_from("<I", data, offset + 4)[0]
        offset += 8
        if start_blocks == 0 and length_blocks == 0:
            break  # invalid/terminator entry

        start = start_blocks * 2048 + data_offset
        length = length_blocks * 1024
        member = data[start:start + length]
        if len(member) < 4:
            fid += 1
            continue

        ident = struct.unpack_from(">I", member, 0)[0]
        name = "file_%04d" % fid
        try:
            if ident == XCOMPRESS_MAGIC:
                # Decoded in the parallel pass below; it becomes a PNG atlas,
                # so advance last_png_idx now to keep descriptor pairing correct.
                jobs.append((fid, member, last_png_idx))
                last_png_idx = fid
            elif ident == PNG_MAGIC:
                with open(os.path.join(out_dir, name + ".png"), "wb") as o:
                    o.write(member)
                last_png_idx = fid
            else:
                # Raw, non-image member: a merge descriptor (chara / bg / 5pb).
                with open(os.path.join(out_dir, name + ".bin"), "wb") as o:
                    o.write(member)
                fragmerge_core.write_extract_sidecar(
                    out_dir, fid, name + ".bin", src_idx=last_png_idx)
        except Exception as e:
            print("  WARN: member %s failed: %s" % (name, e))
        count += 1
        fid += 1
        if count % 100 == 0:
            print("  ... %d members classified" % count, flush=True)

    if not jobs:
        return count

    # Second pass: decode + write the LZXNATIVE members in parallel.
    done = 0
    total = len(jobs)
    if workers > 1 and total > 1:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            fut_to_fid = {ex.submit(_decode_lzx, m): (fid_, src)
                          for fid_, m, src in jobs}
            for fut in as_completed(fut_to_fid):
                fid_, src = fut_to_fid[fut]
                name = "file_%04d" % fid_
                try:
                    dec = fut.result()
                    _write_decoded(out_dir, fid_, dec, src)
                except Exception as e:
                    print("  WARN: member %s failed: %s" % (name, e))
                done += 1
                if done % 100 == 0:
                    print("  ... %d / %d decoded" % (done, total), flush=True)
    else:
        for fid_, m, src in jobs:
            name = "file_%04d" % fid_
            try:
                dec = _decode_lzx(m)
                _write_decoded(out_dir, fid_, dec, src)
            except Exception as e:
                print("  WARN: member %s failed: %s" % (name, e))
            done += 1
            if done % 100 == 0:
                print("  ... %d / %d decoded" % (done, total), flush=True)

    return count


def extract_and_merge(path: str, out_dir: str, merged_dir: str,
                      fmt: str = "bg", scale_override: int | None = None,
                      workers: int | None = None) -> tuple[int, int]:
    """Extract an LNK4 container, then reassemble every descriptor it contains.

    For each ``file_NNNN.bin`` descriptor, merge it with its ``-2``/``-1``
    source PNGs (the crosslnk4 / merge_11ecfrag2 pairing) and write the result
    to ``merged_dir``.  Descriptors that cannot be merged (e.g. the tile map
    references blocks beyond either source) are skipped with a warning.
    """
    extract_lnk4(path, out_dir, workers=workers)
    import glob

    os.makedirs(merged_dir, exist_ok=True)
    bins = sorted(glob.glob(os.path.join(out_dir, "*.bin")))
    merged = skipped = 0
    for b in bins:
        base = os.path.splitext(os.path.basename(b))[0]
        idx = int(base.split("_")[1])
        s1 = os.path.join(out_dir, "file_%04d.png" % (idx - 2))
        s2 = os.path.join(out_dir, "file_%04d.png" % (idx - 1))
        out_path = os.path.join(merged_dir, base + ".png")
        if not (os.path.exists(s1) and os.path.exists(s2)):
            skipped += 1
            print("  skip %s: missing source halves" % base)
            continue
        try:
            arr, _ = fragmerge_core.merge(fmt, [s1, s2], b, scale_override=scale_override)
        except Exception as e:
            skipped += 1
            print("  skip %s: %s" % (base, e))
            continue
        fragmerge_core.save_rgba(arr, out_path)
        merged += 1
    print("merged %d backgrounds -> %s (%d skipped)" % (merged, merged_dir, skipped))
    return merged, skipped


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(
        description="Extract 11eyes LNK4 containers using the real Microsoft "
                    "xcompress.dll (ctypes, Windows) and optionally reassemble "
                    "sliced backgrounds.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("extract", help="extract members to PNG/BIN")
    pe.add_argument("input")
    pe.add_argument("output_dir", nargs="?", default=None)
    pe.add_argument("--workers", type=int, default=None,
                    help="parallel decode threads (default: CPU count)")

    pm = sub.add_parser("extract-merge",
                        help="extract, then reassemble every descriptor to PNG")
    pm.add_argument("input")
    pm.add_argument("output_dir", nargs="?", default=None,
                    help="extraction dir (default: <input>_extract)")
    pm.add_argument("--merged-dir", default=None,
                    help="where to write merged backgrounds (default: <output_dir>/merged)")
    pm.add_argument("--fmt", default="bg", choices=fragmerge_core.FORMATS)
    pm.add_argument("--scale", type=int, default=None,
                    help="5pb src-y atlas scale override")
    pm.add_argument("--workers", type=int, default=None,
                    help="parallel decode threads (default: CPU count)")

    pd = sub.add_parser("dump",
                        help="dump slice mapping from a descriptor .bin as a text grid")
    pd.add_argument("descriptor")
    pd.add_argument("--fmt", default="bg", choices=fragmerge_core.FORMATS)
    pd.add_argument("--out", default=None, help="write to file instead of stdout")

    pdi = sub.add_parser("dump-images",
                         help="extract individual slice images from source PNGs for manual reconstruction")
    pdi.add_argument("descriptor")
    pdi.add_argument("--fmt", default="bg", choices=fragmerge_core.FORMATS)
    pdi.add_argument("--out-dir", required=True, help="output directory for slice PNGs + manifest.json")
    pdi.add_argument("--src1", required=True, help="source image 1 (or only for chara/5pb)")
    pdi.add_argument("--src2", default=None, help="source image 2 (for bg format)")
    pdi.add_argument("--prefix", default="slice", help="filename prefix for slice PNGs")

    pda = sub.add_parser("dump-all",
                         help="extract slice strips for ALL descriptors in an extraction folder")
    pda.add_argument("extract_dir", help="folder with .bin descriptors and .png sources")
    pda.add_argument("--fmt", default="bg", choices=fragmerge_core.FORMATS)
    pda.add_argument("--out-dir", required=True, help="output directory for all strips + manifests")
    pda.add_argument("--prefix", default="slice", help="filename prefix for strip PNGs")

    pr = sub.add_parser("reconstruct-all",
                        help="reconstruct each fragment of every descriptor into its own canvas")
    pr.add_argument("extract_dir", help="folder with .bin descriptors and .png sources")
    pr.add_argument("--fmt", default="bg", choices=fragmerge_core.FORMATS)
    pr.add_argument("--out-dir", required=True, help="output dir for file_NNNN/file_NNNN_frag_MMM/")
    pr.add_argument("--prefix", default="frag", help="filename prefix for reconstructed PNGs")
    pr.add_argument("--scale", type=int, default=None,
                    help="5pb src-y atlas scale override")

    args = p.parse_args()

    if args.cmd == "extract":
        out = args.output_dir or (os.path.splitext(args.input)[0] + "_extract")
        n = extract_lnk4(args.input, out, workers=args.workers)
        print("extracted %d members from %s -> %s" % (n, args.input, out))
    elif args.cmd == "extract-merge":
        out = args.output_dir or (os.path.splitext(args.input)[0] + "_extract")
        merged_dir = args.merged_dir or os.path.join(out, "merged")
        extract_and_merge(args.input, out, merged_dir, args.fmt,
                          args.scale, args.workers)
    elif args.cmd == "dump":
        txt = fragmerge_core.dump_slices(args.fmt, args.descriptor)
        if args.out:
            with open(args.out, "w") as f:
                f.write(txt)
            print("wrote %s" % args.out)
        else:
            print(txt)
    elif args.cmd == "dump-images":
        srcs = [args.src1]
        if args.fmt == "bg":
            if not args.src2:
                p.error("bg format requires --src2")
            srcs.append(args.src2)
        res = fragmerge_core.dump_slices_images(args.fmt, srcs, args.descriptor, args.out_dir, prefix=args.prefix)
        print("wrote %d strips -> %s" % (len(res["strips"]), res["manifest_path"]))
    elif args.cmd == "dump-all":
        import glob
        bins = sorted(glob.glob(os.path.join(args.extract_dir, "*.bin")))
        total = 0
        for b in bins:
            base = os.path.basename(b)
            idx = int(os.path.splitext(base)[0].split("_")[1])
            srcs = _resolve_sources(args.fmt, args.extract_dir, idx)
            if srcs is None:
                print("skip %s: missing source(s)" % base)
                continue
            with open(b, "rb") as f:
                dat = f.read()
            if args.fmt == "bg":
                w0, h0 = struct.unpack_from("<2H", dat, 0)
                p = 4 + w0 * h0 * 2
                count = struct.unpack_from("<H", dat, p)[0]
                frag_count = 1 + count
            elif args.fmt == "chara":
                e1c, _, _, _, _, _, _ = struct.unpack_from("<6H I", dat, 0)
                frag_count = e1c
            else:
                e1c, _ = struct.unpack_from(">2I", dat, 0)
                frag_count = e1c
            desc_folder = os.path.join(args.out_dir, "file_%04d" % idx)
            os.makedirs(desc_folder, exist_ok=True)
            for fi in range(frag_count):
                frag_name = "file_%04d_frag_%03d" % (idx, fi)
                frag_dir = os.path.join(desc_folder, frag_name)
                res = fragmerge_core.dump_slices_images(args.fmt, srcs, b, frag_dir, prefix=args.prefix, frag_idx=fi)
                total += len(res["strips"])
                print("  %s frag %d: %d strips" % (base, fi, len(res["strips"])))
        print("total %d strips -> %s" % (total, args.out_dir))
    elif args.cmd == "reconstruct-all":
        import glob
        bins = sorted(glob.glob(os.path.join(args.extract_dir, "*.bin")))
        total = 0
        for b in bins:
            base = os.path.basename(b)
            idx = int(os.path.splitext(base)[0].split("_")[1])
            srcs = _resolve_sources(args.fmt, args.extract_dir, idx)
            if srcs is None:
                print("skip %s: missing source(s)" % base)
                continue
            res = fragmerge_core.reconstruct_fragments(
                args.fmt, srcs, b, args.out_dir, prefix=args.prefix,
                scale_override=args.scale)
            total += res["fragment_count"]
            print("  %s: %d fragments reconstructed" % (base, res["fragment_count"]))
        print("total %d reconstructed fragments -> %s" % (total, args.out_dir))


if __name__ == "__main__":
    main()
