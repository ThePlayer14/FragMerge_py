# Usage Reference — FragMerge Tools

## Commands Overview

| Script | Subcommands |
|--------|-------------|
| `lnk4_extract.py` | `extract`, `extract-merge`, `dump`, `dump-images`, `dump-all` |
| `lnk4_extract_xcompress.py` | `extract`, `extract-merge`, `dump`, `dump-images`, `dump-all` |
| `fragmerge_gui.py` | (GUI only) |

---

## lnk4_extract.py — libmsxca backend (Linux)

```bash
python3 lnk4_extract.py <subcommand> [options]
```

### extract
Extract all members from an LNK4 container.

```bash
python3 lnk4_extract.py extract INPUT.dat [OUTPUT_DIR] [--workers N]
```
- `OUTPUT_DIR` defaults to `INPUT_extract/`
- `--workers N` parallel decode threads for LZXNATIVE members (default: CPU count). `ctypes` releases the GIL during the native decode, and `libmsxca` / `xcompress.dll` are reentrant, so large containers extract noticeably faster. Set `--workers 1` to force serial.
- Produces `file_NNNN.png` (TIMG images) and `file_NNNN.bin` (descriptors)
- Creates sidecar `file_NNNN.json` for each descriptor

### extract-merge
Extract + reassemble every descriptor in one pass.

```bash
python3 lnk4_extract.py extract-merge INPUT.dat [OUTPUT_DIR] \
    [--merged-dir DIR] [--fmt FORMAT] [--scale N] [--workers N]
```
- `--merged-dir` defaults to `OUTPUT_DIR/merged/`
- `--fmt` one of `chara`, `bg`, `5pb` (default: `bg`)
- `--scale` 5pb src-y atlas override (e.g. 512, 1024). Note: the correct scale for Steins;Gate X360 is always `1024`.
- `--workers N` parallel decode threads (default: CPU count)

### dump
Print slice grid as text.

```bash
python3 lnk4_extract.py dump DESCRIPTOR.bin [--fmt FORMAT] [--out FILE.txt]
```
- Output to stdout or `--out` file

### dump-images
Extract horizontal strips for ONE descriptor.

```bash
python3 lnk4_extract.py dump-images DESCRIPTOR.bin \
    --fmt FORMAT \
    --src1 SOURCE1.png \
    [--src2 SOURCE2.png] \
    --out-dir OUTDIR \
    [--prefix PREFIX]
```
- `chara`/`5pb`: only `--src1`
- `bg`: requires `--src1` (index-2) and `--src2` (index-1)
- Output: `slice_XXXX_syYYY_exZZZ_lenNNN.png` + `manifest.json`

### dump-all
Batch extract strips for ALL descriptors in an extraction folder.

```bash
python3 lnk4_extract.py dump-all EXTRACT_DIR \
    --fmt FORMAT \
    --out-dir OUTROOT \
    [--prefix PREFIX]
```
- Creates per-descriptor folder: `file_NNNN/`
- Inside each: per-fragment subfolder `file_NNNN_frag_MMM/`
- Each fragment folder: strips + `manifest.json` with `"fragment_index": MMM`

---

## lnk4_extract_xcompress.py — xcompress.dll backend

Identical CLI to `lnk4_extract.py`. Uses the`xcompress.dll` via ctypes.

```cmd
python lnk4_extract_xcompress.py extract game_bg.dat out/
```
Place `xcompress.dll` (x64) next to script or in PATH.

---

## fragmerge_gui.py — PySide6 Viewer (tabbed)

```bash
python3 fragmerge_gui.py
```

The layout is in `src/fragmerge_gui.ui`; after editing it in Qt Designer,
rebuild the binding with `pyside6-uic fragmerge_gui.ui -o fragmerge_gui_ui.py`.

### Layout
| Panel | Contents |
|-------|----------|
| Left (Merge tab): Format | Radio buttons: `11eyes chara` / `11eyes bg` / `5pb` / sg (PC) |
| Left (Merge tab): Files | Source 1, Source 2 (bg), Descriptor `.bin` pickers |
| Left (Merge tab): Auto | "Open (auto...)" — resolves triplet from any extracted file |
| Left (Merge tab): Folder | "Open folder (list descriptors)" — scans for `.json` sidecars |
| Left (Merge tab): 5pb scale | Text entry: `auto` / `256` / `512` / `1024` / `2048` |
| Left (Merge tab): Actions | Preview / Save PNG/BMP |
| Left (Merge tab): Fragments | Scrollable checkbox list (appears after Preview) — toggle to include/exclude |
| Left (Debug tab): Single | Dump slices (text grid) / Dump slice images (PNGs) |
| Left (Debug tab): Batch | format + **Workers** spin (parallel fragment dumps) + extraction folder + output folder → Run batch dump |
| Open container (.dat) | "Open (auto...)" on a `.dat` extracts it with CPU-count parallel decode into a temp dir |
| Right: Preview | Scrollable canvas, always visible; zoom − / 100% / + buttons above it (100% resets to fit-to-view) |

### Workflow
1. Select **Format**
2. Click **"Open (auto...)"** → pick any `file_NNNN.png` or `file_NNNN.bin` from an extracted folder
3. Click **Preview** → merged image appears
4. Toggle fragment checkboxes to isolate regions
5. **Debug** tab → **Dump slices (text grid)** → save ASCII grid
6. **Dump slice images (PNGs)** → pick folder, saves strips + manifest
7. **Save PNG/BMP** → save merged result

---
## Supported Formats

| Format | Block | Trim | Sources | Container | Games |
|--------|-------|------|---------|-----------|-------|
| `chara` | 32×32 | 1px border | 1 (adjacent member) | LNK4 (`chara.dat`) | 11eyes character art |
| `bg` | 16×16 | none | 2 (`-2`/`-1` halves) | LNK4 (`bg.dat`) | 11eyes backgrounds |
| `5pb` | 32×32 | none | 1 (float coords) | LNK4 (chara/bg)| 5pb / MAGES Xbox 360 |
| `sg` | 32×32 | none | 1 (`.lay` + `.png`) | MPK (unpacked) | Steins;Gate PC / MAGES engine |

### chara format
- 32×32 source blocks, **1px border trimmed** each side → 30×30 output
- Adjacent members: even index = atlas PNG, odd index = descriptor `.bin`
- Descriptor `file_NNNN.bin` pairs with atlas `file_NNNN-1.png` (preceding member)
- This format is for 11eyes Crossover only 

### bg format
- 16×16 source blocks, **no trim**
- Two source halves: `file_(i-2).png` and `file_(i-1).png`
- This format is for 11eyes Crossover only 

### 5pb format
- 32×32 blocks, no trim
- Big-endian descriptor: `[u32 entry1_count][u32 entry2_count]` header
- Source coordinates: `src_x = float × 2048 − 1`, `src_y = float × scale − 1`
- Scale factor: always **1024** for Steins;Gate X360 (not atlas-height-dependent)
- Alpha blending: overlay groups (i > 0) use alpha-over compositing
- Likely works for 5pb Xbox 360 games. Tested with SG 360 and Code_18.

### sg format
- 32×32 blocks, no trim
- `.lay` descriptor + `.png` atlas (from MPK container)
- Dependence chain: base → sub → dep → overlay
- Source coordinates: `src_x = float × 2048 − 1`, `src_y = float × atlas_h − 1`

---

## File Naming Conventions

| File | Pattern | Description |
|------|---------|-------------|
| Source PNG (chara/5pb) | `file_NNNN.png` | Preceding member (idx-1) |
| Source PNG (bg half 1) | `file_NNNN.png` | Index = descriptor index - 2 |
| Source PNG (bg half 2) | `file_NNNN.png` | Index = descriptor index - 1 |
| Source PNG (sg) | `NAME.png` | Paired with `NAME_.lay` |
| Descriptor | `file_NNNN.bin` | Slice mapping data |
| Descriptor (sg) | `NAME_.lay` | MAGES sprite descriptor |
| Sidecar | `file_NNNN.json` | Auto-resolve metadata |
| Merged output | `file_NNNN.png` | In `--merged-dir` |
| Strip PNG | `slice_XXXX_syYYY_exZZZ_lenNNN.png` | Horizontal source run |
| Fragment folder | `file_NNNN_frag_MMM/` | Per-fragment strips |
| Reconstructed PNG | `frag_MMM.png` | Standalone fragment output |

---

## Manifest.json Schema

### dump-images manifest
```json
{
  "format": "bg",
  "descriptor": "file_0328.bin",
  "fragment_index": 0,
  "block_size": [16, 16],
  "source_images": ["file_0326.png", "file_0327.png"],
  "strips": [
    {
      "file": "slice_0000_sy000_ex000_len128.png",
      "src_y": 0,
      "start_ex": 0,
      "length": 128,
      "block_w": 16,
      "block_h": 16,
      "actual_w": 1280,
      "actual_h": 16,
      "out_of_bounds": false
    }
  ],
  "placements": [
    {
      "dest_x": 0,
      "dest_y": 0,
      "strip_index": 0,
      "strip_file": "slice_0000_sy000_ex000_len128.png",
      "offset_in_strip": 0
    }
  ]
}
```

### reconstruct-all manifest
```json
{
  "format": "5pb",
  "descriptor": "file_0001.bin",
  "fragment_count": 4,
  "fragments": [
    {
      "index": 0,
      "file": "file_0001_frag_000/frag_000.png"
    },
    {
      "index": 1,
      "file": "file_0001_frag_001/frag_001.png"
    }
  ]
}
```

---

## Examples

### Full pipeline: extract → merge → debug
```bash
# 1. Extract LNK4
python3 lnk4_extract.py extract game_bg.dat bg_out/

# 2. Reassemble all backgrounds
python3 lnk4_extract.py extract-merge game_bg.dat bg_out/ --fmt bg

# 3. Debug one descriptor
python3 lnk4_extract.py dump bg_out/file_0328.bin --fmt bg --out grid.txt
python3 lnk4_extract.py dump-images bg_out/file_0328.bin \
    --fmt bg --src1 bg_out/file_0326.png --src2 bg_out/file_0327.png \
    --out-dir slices_0328/

# 4. Batch all fragments
python3 lnk4_extract.py dump-all bg_out/ --fmt bg --out-dir all_frags/
```

### 5pb with scale override
```bash
python3 lnk4_extract.py extract-merge game.dat out/ --fmt 5pb --scale 512
```

### SG X360 chara.dat (uses 5pb format)
```bash
# Extract
python3 lnk4_extract.py extract chara.dat sg360_out/

# Reassemble all character sprites
python3 lnk4_extract.py extract-merge chara.dat sg360_out/ --fmt 5pb

# Reconstruct all fragments
python3 lnk4_extract.py reconstruct-all sg360_out/ --fmt 5pb --out-dir recon/
```

### Steins;Gate PC (sg format)
```bash
# After unpacking MPK:
# NAME.png + NAME_.lay pairs in the unpacked folder

# Reconstruct all fragments for a sprite
python3 lnk4_extract.py reconstruct-all mpk_out/ --fmt sg --out-dir recon/
```


### GUI: open extracted folder
```bash
python3 fragmerge_gui.py
# Click "Open folder (list descriptors)" → select bg_out/
# Click any descriptor in list → Preview
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `libmsxca.so not found` | Not built or not copied from `libs` | copy over or build manually|
| `xcompress.dll not found` | DLL missing | Copy x64 `xcompress.dll` next to script |
| `wine: command not found` | Wine not installed | `sudo apt install wine64` |
| GUI: "Need source image(s) + .dat" | Files not auto-resolved | Pick Format first, then Open |
| GUI: fragment list empty | Preview not run | Click Preview first |
| Scrambled 5pb output | Wrong scale factor | Use `--scale 1024` (correct for SG X360) |

---
