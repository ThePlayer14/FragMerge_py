# Format Investigations

Forensic findings from reverse-engineering the 11eyes CrossOver / 5pb / MAGES
sprite fragment formats. This is the *investigation log* — how we discovered
what each field means, what broke, and what the fixes were. For the cleaned-up
spec, see FORMATS.md.

---

## 1. LNK4 container structure

The LNK4 container is a little-endian archive used by 11eyes CrossOver (Xbox
360) and other MAGES/5pb titles.

**Header:**

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0 | 4 | magic | ASCII `LNK4` |
| 4 | 4 | `data_offset` | LE `<I` — start of member data (in bytes) |

**TOC (table of contents):**

Each entry is 8 bytes, starting at offset 8:

| Field | Size | Notes |
|-------|------|-------|
| `start_blocks` | 4 | LE `<I` — member data starts at `start_blocks × 2048 + data_offset` |
| `length_blocks` | 4 | LE `<I` — member length in 1024-byte blocks (`length_blocks × 1024`) |

TOC is terminated by a `{0, 0}` entry.

**SG X360 variant** uses the same formula (`start_blocks × 2048 + data_offset`
for absolute offset, `length_blocks × 1024` for length).

**Member detection** — classify each member by its first 4 bytes (big-endian
`>I`):

| Magic | Classification | Output |
|-------|---------------|--------|
| `0FF512EE` (LZXNATIVE) | Compressed blob — decompress → check TIMG | `file_NNNN.png` (TIMG) or `file_NNNN.bin` + `.json` sidecar |
| `89504E47` (PNG) | Raw PNG | `file_NNNN.png` |
| anything else | Raw descriptor | `file_NNNN.bin` + `.json` sidecar |

Do **not** apply the TIMG `depth != 0` heuristic to raw members — chara
descriptors are raw members whose bytes can coincidentally look like a TIMG,
which makes the extractor crash ("not enough image data") on fragmented
descriptors.

---

## 2. chara format (11eyes `chara.dat`)

Used by 11eyes CrossOver (Xbox 360) for character sprite fragments.

**Structure:** 32×32 source blocks, **1px border trimmed** on each side →
30×30 output. The 1-pixel border is the block boundary artifact from the atlas
packing.

**Pairing:** Adjacent members in `chara.dat` — even index = atlas PNG, odd
index = descriptor `.bin`. A descriptor `file_NNNN.bin` pairs with atlas
`file_NNNN-1.png` (the preceding member). The sidecar records this
automatically.

**Descriptor header** (little-endian):

```
struct.unpack_from("<6H I", dat, 0)
→ e1c, e2c, w, h, w2, h2, unk
```

`e1c` = number of entry1 groups (typically 2–5), `e2c` = total entry2 count.

**Entry1** (16 bytes each):

```
u1, u2, e2off, ox, oy, wb, hb  =  struct.unpack_from("<2H I 4H", dat, off)
```

**Entry2** — index pairs pointing into the atlas.

**Alpha compositing:** The chara merge uses `_alphablend()` for overlay blocks
(line 392–393 of `fragmerge_core.py`), skipping fully-transparent rows:

```python
if src_row[:, 3].any():
    _alphablend(dst_row, src_row)
```

This is the correct approach: base layer (i=0) uses direct copy, overlay
layers (i>0) use alpha blending.

---

## 3. bg format (11eyes `bg.dat`)

Used by 11eyes CrossOver (Xbox 360) for background sprite fragments.

**Structure:** 16×16 source blocks, **no trim**.

**Sources:** Two source halves — descriptor at index `i` uses
`file_(i-2).png` and `file_(i-1).png`.

**Descriptor header** (little-endian):

```
struct.unpack_from("<2H", dat, 0)
→ w0, h0   (width and height of base in blocks)
```

---

## 4. 5pb format (Xbox 360 / MAGES `chara.dat`)

Used by 5pb/MAGES Xbox 360 titles (Steins;Gate X360, Code_18) for
character sprite fragments. This is the most complex format because it uses
**floating-point coordinates** and **big-endian** throughout.

**Block size:** 32×32 pixels, no trim.

**Source:** Single atlas PNG. All fragment descriptors reference a single atlas
(the preceding member in the container).

### Descriptor structure

**FRAGHDR** (8 bytes, big-endian):

```python
struct.unpack_from(">2I", dat, 0)
→ num_entries1, num_entries2
```

**FRAGENTRY1** (12 bytes each, big-endian):

```python
struct.unpack_from(">2H 2I", dat, offset)
→ u1, u2, e2off, ox_or_flags
```

- `u1` = group type/layer indicator
- `u2` = variant/sub-index
- `e2off` = offset into entry2 pool
- `ox` = additional flags

The `u1` values encode the layer hierarchy:

| u1 | Meaning |
|----|---------|
| 0 | Base layer (drawn first) |
| 8192 (0x2000) | Secondary layer (overlay) |
| 16384 (0x4000) | Sub layer (e.g. expression component) |

Entry1 groups form a hierarchy: base → secondary → sub. The `u2` values
encode: for u1=16384 → `layer_group × 256 + variant_index`.

**FRAGENTRY2** (16 bytes each, big-endian):

```python
struct.unpack_from(">4f", dat, offset)
→ dst_x, dst_y, src_x, src_y
```

All four values are **big-endian IEEE 754 floats**.

### Coordinate mapping

- `src_x = src_x_float × 2048 − 1` (source pixel X in atlas)
- `src_y = src_y_float × scale − 1` (source pixel Y in atlas)
- `dst_x, dst_y` = destination position (can be negative; canvas is sized from
  min/max of all dst coords)

The destination coordinate space is screen-centered (similar to a pixel shader
parameter, as asmodean suspected).

### The scale factor

The `_5pb_scale(src_h)` function returns the atlas height scale factor for
`src_y`. After extensive investigation:

**The correct scale is always 1024**, regardless of atlas height.

The `src_y` floats in 5pb descriptors are normalized to a fixed virtual height
of 1024, not the actual atlas pixel height. This was verified correct for:

- 224px atlas (file_0018.png, sgchara.dat) → scale should be 1024
- 448px atlas (file_0010.png, sgchara.dat) → scale should be 1024

asmodean's C++ heuristic (`merge_5pbfrag.cpp`) tries:

```cpp
if (atlas_h <= 256)  scale = 256;
else if (atlas_h <= 512)  scale = 512;
else if (atlas_h <= 1024)  scale = 1024;
else  scale = 2048;
```

This is **wrong** for Steins;Gate X360 where all atlases use 1024. The
corrected function returns `1024` unconditionally, resolving all coordinate
scrambling.

### Per-pixel copy behavior

asmodean's C++ (`merge_5pbfrag.cpp`) does **per-pixel** copy, not block-level:

```cpp
for (int x = 0; x < 32; x++) {
    for (int y = 0; y < 32; y++) {
        src_pix = src[(unsigned long)(src_x + x)][(unsigned long)(src_y + y)];
        dst_pix = out[(unsigned long)(dst_x + x)][(unsigned long)(dst_y + y)];
        *dst_pix = *src_pix;
    }
}
```

The `(unsigned long)` cast of a float truncates toward zero. When `src_y` is
fractional (e.g. −0.5), this produces a 1-row shift compared to a block-level
slice `src[sy:sy+32]` where `sy = int(sy_f)`.

Python's `int()` also truncates toward zero, matching the C++ behavior. The
per-pixel approach was verified to produce **0 content-vs-content pixel
differences** against the C++ Wine reference output for file_0010/file_0011.

### Alpha blending for overlay groups

**Bug:** Overlay entry1 groups (i > 0) were using direct pixel copy
(`np.copyto`), which overwrites opaque base-layer pixels with fully-transparent
overlay pixels, punching holes in the sprite.

**Example:** file_0043 (Daru) — overlay groups placed
mostly-transparent blocks at dst=(605,321), the nose area. Direct copy
overwrote opaque pixels with alpha=0, creating a dark ~30×30 rectangle
artifact.

**Fix:** For overlay groups (i > 0), use `_alphablend_block` instead of
`np.copyto`:

```python
if i == 0:
    np.copyto(db, sb)
else:
    _alphablend_block(db, sb)
```

This matches the chara format's existing behavior (line 392–393 of
`fragmerge_core.py`).

**Results:**

| Metric | Before fix | After fix |
|--------|-----------|-----------|
| file_0043 nose transparent pixels | 622 | 0 |
| file_0043 nose opaque pixels | 278/900 | 900/900 |
| file_0018 total transparent change | — | 56 pixels (0.01%) |
| Test suite | 20 passed, 1 failed | 21 passed |

### Known groups per atlas

| Atlas | Descriptor | entry1 groups | entry2 count | Content |
|-------|-----------|---------------|--------------|---------|
| file_0010.png (2048×448) | file_0011.bin | 25 (1 base, 6 secondary, 18 sub) | 1118 | Kurisu close-up |
| file_0018.png (2048×224) | file_0019.bin | 37 | 514 | Kurisu full-body |
| file_0042.png (2048×672) | file_0043.bin | 27 (1 base, 9 secondary, 17 sub) | 1600 | Daru |

---

## 5. sg format (Steins;Gate PC / MAGES engine, MPK)

Used by Steins;Gate Steam, S;G0, Chaos;Child, and other MAGES PC titles.

**Structure:** 32×32 source blocks, no trim.

**Container:** MPK (simple little-endian archive; individual files may be
zlib-compressed, flagged per-entry). After unpacking `chara.mpk`, each sprite
is a pair:

- `NAME.png` — source atlas (all 32×32 chunks concatenated)
- `NAME_.lay` — descriptor (the trailing `_` is dropped from the atlas stem,
  so `CRS_ALA_.lay` pairs with `CRS_ALA.png`)

### .lay layout

```
[u32 sprite_count][u32 chunk_count]
sprite entries (12B): [u8 A][u8 B][u8 C][u8 D][u32 chunk_off][u32 chunk_count]
chunk entries  (16B): [f32 dst_x][f32 dst_y][f32 src_x][f32 src_y]   # then trailing junk
```

`D` is a sprite-type nibble forming a **dependence chain**:

| D value | Meaning |
|---------|---------|
| `0x00` | Base — drawn first |
| `0x20` | Sub (e.g. a face) — depends on the base |
| `0x30`/`0x40`/`0x60` | Dep (e.g. a mouth) — depends on the sub whose id is `B` |
| `0x50` | Overlay — blended on top (significant alpha) |

Chunks are 32×32 blocks; `src` points at pixel `[1,1]` so the tool subtracts
1, `dst` is the block's upper-left corner in a screen-centered coordinate
space (can be negative — the canvas is sized from the min/max `dst`).

### .lay vs .stream — different formats

The `.lay` files (PC/Steins;Gate Steam) and `.stream` files (Xbox 360) are
**completely different formats**:

- `.lay` = little-endian sprite descriptor + 32×32 chunk float coords +
  dependence chain
- `.stream` = LNK4 decompressed member (can be TIMG atlas or descriptor blob)

**Functional equivalents:**

| Xbox 360 | PC | Notes |
|----------|-----|-------|
| `.bin` descriptor | `.lay` | Same role, different encoding |
| `.stream` (TIMG atlas) | `.png` | Same atlas data, different container |

---

## 6. Alpha handling

The Xbox 360 TIMG atlases store **straight (non-premultiplied) alpha** — the
RGB is the true colour and the alpha channel is separate coverage.

Do **not** "un-premultiply" these atlases. Dividing the RGB by `alpha/255` is
wrong for straight-alpha data: a semi-transparent edge pixel whose stored RGB is
a normal (bright) colour would be inflated far above 255 and clip to white,
leaving a white halo/fringe around sprites.

The Steins;Gate PC (`sg`) atlases are ordinary PNG and likewise straight alpha.

**Verified by test:** `test_straight_alpha_no_premultiply` confirms atlas
pixel values match xbdecompress output with no alpha correction applied.

---

## 7. Sidecar files

During LNK4 extraction, each `file_NNNN.bin` gets a `file_NNNN.json`:

```json
{
  "index": 328,
  "descriptor": "file_0328.bin",
  "sources": {
    "single": [],
    "bg": ["file_0326.png", "file_0327.png"]
  }
}
```

The GUI uses these for instant auto-resolve. (`sg` does not use sidecars — the
`.lay`/`.png` pairing is by filename stem.)

---

## 8. _detect_fmt — heuristic format detection

A heuristic function to identify the descriptor format of raw `.bin` data:

```python
def _detect_fmt(dat: bytes) -> str | None:
    if len(dat) < 8:
        return None
    if dat[:4] == b"\x89PNG":
        return None
    n1, n2 = struct.unpack_from(">2I", dat, 0)
    if n1 < 1 or n2 < 1:
        return None
    if 8 + n1 * 12 + n2 * 16 > len(dat):
        return None
    return "5pb"
```

This detects 5pb descriptors by their big-endian `>2I` FRAGHDR signature.
Returns `None` for PNGs, chara, bg, and sg formats (which use little-endian
headers or different structures).

---


## 9. Gotchas and cross-cutting concerns

- **5pb descriptors are big-endian throughout**, while chara/bg/sg are
  little-endian. This is the key distinguishing feature for `_detect_fmt`.

- The **5pb scale factor** is not derived from atlas height — it is always 1024.
  asmodean's C++ heuristic is wrong for Steins;Gate X360.

- **SG X360 `bg.dat`** is NOT the `bg` merge format — it is a flat container of
  TIMG backgrounds with no descriptors. The `bg` format is
  specific to 11eyes.

- **SG X360 `chara.dat`** uses the **`5pb` format** (asmodean's
  `merge_5pbfrag.cpp` v1.01), not the `chara` format. The `chara` format is
  specific to 11eyes.

- **Alpha blending is required** for overlay groups in the 5pb merge. Direct
  copy punches holes in the sprite by overwriting opaque pixels with
  transparent ones. The chara format already handles this correctly.
