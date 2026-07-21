
# FragMerge — LNK4 Slice Reassembler

Python reimplementation of asmodean's `exlnk4` merge tools for Xbox 360 games (11eyes CrossOver, 5pb/MAGES titles). Extracts LNK4 containers and reassembles sliced background/character art.

## Features

- **LNK4 extraction** — pure Python (no Windows DLLs needed) via `libmsxca` (LZXNATIVE decompressor)
- **Extraction on Windows** — uses the `xcompress.dll` via ctypes (Windows).
- **Slice reassembly** — `chara`, `bg`, `5pb`, `sg` formats (matches original C tools exactly)
- **PySide6 GUI** — tabbed (Merge / Debug), live preview on the right, toggle fragments, save PNG/BMP, dump debug data
- **Debug dumping** — text grid, horizontal strip images with manifest, batch per-fragment output
- **Alpha blending** — correct alpha-over compositing for overlay layers (5pb and sg formats)

## Project Structure

```
.
│   ├── fragmerge_core.py          # Core logic (merge, parsers, debug dumps)
│   ├── fragmerge_gui.py           # PySide6 viewer (uses generated Ui)
│   ├── fragmerge_gui.ui           # Qt Designer layout (tabbed)
│   ├── fragmerge_gui_ui.py        # Generated from .ui by pyside6-uic (rebuild on .ui change)
│   ├── lnk4_extract.py            # LNK4 extractor (libmsxca)
│   ├── lnk4_extract_xcompress.py  # LNK4 extractor (xcompress.dll, Windows)
└── docs/                          # Documentation about the researches
```

## Supported Formats

| Format | Block | Trim | Sources | Container | Games |
|--------|-------|------|---------|-----------|-------|
| `chara` | 32×32 | 1px border | 1 (adjacent member) | LNK4 (`chara.dat`) | 11eyes character art |
| `bg` | 16×16 | none | 2 (`-2`/`-1` halves) | LNK4 (`bg.dat`) | 11eyes backgrounds |
| `5pb` | 32×32 | none | 1 (float coords) | LNK4 | 5pb / MAGES Xbox 360 |
| `sg` | 32×32 | none | 1 (`.lay` + `.png`) | MPK (unpacked) | Steins;Gate PC / MAGES engine |

## Documents
- The write-ups are in the `/docs` folder.

## Requirements

- Python 3.10+
- `numpy`, `Pillow`, `PySide6`
- `libmsxca.so` (build from `/extras/libmsxca.tar.gz`) — for `lnk4_extract.py`
- `xcompress.dll` (x64) — for `lnk4_extract_xcompress.py` (Windows) or Wine (Linux)

```bash
pip install numpy Pillow PySide6
```

### Creating a virtual environment for Python

* If your machine does not have Python installed, you can use `uv` to create a local environment with its own packages and managed versions.
* You can read instructions for how to install `uv` at the [uv homepage](https://docs.astral.sh/uv/) and the specific instructions for creating a [virtual environment](https://docs.astral.sh/uv/pip/environments/#creating-a-virtual-environment).

## Rebuilding the GUI from the .ui file

The GUI layout lives in `fragmerge_gui.ui` (edit with Qt Designer). After
changing it, regenerate the Python binding so the GUI picks it up:

```bash
cd main
pyside6-uic fragmerge_gui.ui -o fragmerge_gui_ui.py
python3 fragmerge_gui.py
```

`fragmerge_gui.py` subclasses the generated `Ui_FragMergeApp`, so any new
widget you add in Designer is available as `self.<objectName>` once you
re-run `pyside6-uic`.


## Quick Start

```bash
# Extract LNK4 container
python3 lnk4_extract.py extract game_bg.dat output_folder/

# Extract and reassemble all backgrounds
python3 lnk4_extract.py extract-merge game_bg.dat output_folder/ --fmt bg

# Dump slice grid for manual inspection
python3 lnk4_extract.py dump output_folder/file_0328.bin --fmt bg

# Dump horizontal strips for a single descriptor
python3 lnk4_extract.py dump-images output_folder/file_0328.bin \
    --fmt bg --src1 output_folder/file_0326.png --src2 output_folder/file_0327.png \
    --out-dir slices/

# Batch dump ALL descriptors with per-fragment folders
python3 lnk4_extract.py dump-all output_folder/ --fmt bg --out-dir all_frags/

# Batch RECONSTRUCT every fragment of every descriptor as its own PNG
python3 lnk4_extract.py reconstruct-all output_folder/ --fmt chara --out-dir recon/

# Launch GUI
python3 fragmerge_gui.py
```

## How extraction decides file types

See the documentation at `/docs`.

## GUI Usage

The left side is a **tabbed** panel; the right side is always the **live preview**.

**Merge tab**
1. **Format** — select `11eyes chara` / `11eyes bg` / `5pb` / `sg (PC)`
2. **Files** — pick Source 1, Source 2 (bg only), Descriptor `.dat`/`.bin`
3. **Open (auto)** — point at any file from an extracted LNK4 folder; auto-resolves the triplet.   
This function also works for loading SG PC images one-by-one.
4. **Open folder** — scans for sidecar `.json` files, lists all descriptors
5. **Preview** — reassembles and shows result; fragment checkboxes appear
6. **Fragments** — toggle individual fragments (All / None); preview updates live
7. **Save PNG/BMP** — saves the merged result

**Debug tab**
1. **Dump slices (text grid)** — saves ASCII grid of source coordinates (uses current format/srcs/descriptor)
2. **Dump slice images (PNGs)** — saves horizontal strips + `manifest.json`
3. **Batch dump all** — pick a format, an extraction folder, an output folder, then Run; each descriptor becomes `file_NNNN/file_NNNN_frag_MMM/` with strips + `manifest.json`
4. **Reconstruct fragments** — pick a format, an extracted folder, and an output folder, then Run. Renders each fragment of every descriptor **in isolation** (every other fragment hidden), producing `file_NNNN/file_NNNN_frag_MMM/frag_MMM.png` + `reconstruct_manifest.json`. This is the inverse of `dump-all`: instead of slicing one fragment out of the full merged image, it builds a clean standalone PNG of that single fragment (no other fragments overlapping it). Useful for verifying per-fragment correctness or exporting individual sprites.

## Debug Output

### `dump` — Text Grid
```
format: bg   descriptor: file_0328.bin
dest block grid (rows = dest y, cols = dest x); cell = source (ex,ey); '..' = skip (0xFF,0xFF)
 0,00  0,00  0,00  ...  46,01 47,01  0,00  1,00  2,00 ...
 ...
```

### `dump-images` — Horizontal Strips
```
/slices/
├── slice_0000_sy000_ex000_len128.png
├── slice_0001_sy001_ex000_len128.png
└── manifest.json
```
Manifest maps each destination block → strip file + offset.

### `dump-all` — Per-Fragment Batch
```
/all_frags/
├── file_0328/
│   ├── file_0328_frag_000/
│   │   ├── manifest.json
│   │   └── slice_*.png
│   ├── file_0328_frag_001/
│   └── ...
└── file_1225/
    ├── file_1225_frag_000/
    ...
    └── file_1225_frag_017/
```

### `reconstruct-all` — Standalone Per-Fragment PNGs
```
/recon/
├── file_0328/
│   ├── reconstruct_manifest.json
│   ├── file_0328_frag_000/
│   │   └── frag_000.png
│   ├── file_0328_frag_001/
│   │   └── frag_001.png
│   └── ...
└── file_1225/
    ├── reconstruct_manifest.json
    ├── file_1225_frag_000/
    │   └── frag_000.png
    ...
    └── file_1225_frag_017/
        └── frag_017.png
```
Each `frag_MMM.png` is exactly the pixels of `merge(fmt, srcs, dat, enabled={MMM})`
— i.e. that one fragment rendered with nothing else present (transparent
everywhere it is not painted). The `reconstruct_manifest.json` records the
fragment count and per-fragment metadata.

## Sidecar Files

During LNK4 extraction each `file_NNNN.bin` gets a `file_NNNN.json` recording
its index and source PNGs; the GUI uses these for instant auto-resolve. See
**FORMATS.md** for the schema. (`sg` does not use sidecars — the
`.lay`/`.png` pairing is by filename stem.)

## Known Issues
- The `sg` format's dependence chain (`D` nibble values `0x30`/`0x40`/`0x60`) is partially implemented — basic base/sub/dep compositing works, but some edge cases in multi-dep chains may not render identically to the game engine.

## Fixes made for the 5pb format

### Alpha blending for 5pb overlay groups

Overlay entry1 groups (i > 0) now use `_alphablend_block` instead of direct
pixel copy. This fixes transparent pixels overwriting opaque content in the
base layer (e.g. the file_0043 nose artifact — 622 transparent pixels → 0).

### `_detect_fmt` — heuristic format detection

New function in `lnk4_extract.py` identifies 5pb descriptors by their
big-endian `>2I` FRAGHDR signature. Returns `"5pb"` for valid descriptors,
`None` for PNGs and other formats.

### 5pb scale factor corrected

The `_5pb_scale` function now always returns `1024` (not the heuristic based
on atlas height). This fixes coordinate scrambling for Steins;Gate X360
atlases where `src_y` floats are normalized to a fixed virtual height of 1024.

# References

- Original tools: asmodean `exlnk4` (`merge_11ecfrag.cpp`, `merge_11ecfrag2.cpp`, `merge_5pbfrag.cpp`)
- LNK4 container: 11eyes CrossOver / 5pb Xbox 360 games
- Compression: Microsoft XMemCompress (LZXNATIVE, `0FF512EE`)
- Spec: Xbox 360 Help CHM file
- Format investigations: FORMAT_INVESTIGATIONS.md

# Note
- OpenCode's Zen models were used during the development and testing phase for this project.

# Acknowledgements

* asmodean for the exlnk4 / 11ecfrag / 5pbfrag utilities' code
* Timo654 for the image extraction code for 11eyes `chara`/`bg` atlases and LNK4 extraction improvements
* AbsurdlySuspicious for the `.lay` files' documentation
