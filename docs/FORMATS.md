# Formats

This document consolidates everything about the game-specific sprite formats
that FragMerge understands. A more in-depth doc is `FORMAT_INVESTIGATIONS.md`.

## Supported formats

| Format | Block | Trim | Sources | Container | Games |
|--------|-------|------|---------|-----------|-------|
| `chara` | 32×32 | 1px border | 1 (adjacent member) | LNK4 (`chara.dat`) | 11eyes character art |
| `bg`    | 16×16 | none       | 2 (`-2`/`-1` halves) | LNK4 (`bg.dat`) | 11eyes backgrounds |
| `5pb`   | 32×32 | none       | 1 (float coords) | LNK4 | 5pb / MAGES Xbox 360 |
| `sg`    | 32×32 | none       | 1 (`.lay` + `.png`) | MPK (unpacked) | Steins;Gate PC / MAGES engine |

All four are handled by `fragmerge_core.merge(fmt, srcs, dat, enabled=…)`,
which reassembles the source atlas(es) into the final sprite using the binary
descriptor. "Fragments" are the merge tool's selectable units (set `enabled` to
a subset to render only those).

## Background — the asmodean original

The original tools are asmodean's `exlnk4` set, described on their blog
(2009/11/17). The live site has been down since around November 2025, but the
entry is preserved in web archives, e.g. the Wayback Machine:
`https://web.archive.org/web/2025/https://asmodean.reverse.net/pages/exlnk4.html`.

> This was irritating dealing with the block/delta image format, especially
> having to do so three different ways. Still, it's something I haven't seen
> before and was a bit interesting. The floating-point version I suspect is
> reassembled on the GPU, maybe in a pixel shader?
>
> Usage of the merge tools is unusually complicated. The first parameter is the
> bitmap and the next is the delta data file (no extension). Passing `auto`
> where supported will guess paired filenames; it's usually right.
>
> - `merge_5pbfrag` works with STEINS;GATE.
> - `merge_11ecfrag` works with deltas in 11eyes CrossOver's `chara.dat`.
>   Extracting everything will consume a *lot* of space.
> - `merge_11ecfrag2` works with deltas in 11eyes CrossOver's `bg.dat`. Note
>   there are two bitmaps each for this one.

Mapping to this reimplementation:

| Original tool | Container | Our `fmt` | Notes |
|---------------|-----------|-----------|-------|
| `merge_5pbfrag` | 5pb format LNK4 `.dat `(`chara`) | `5pb` | Float coords → `src_y` scaled by atlas (the "GPU/pixel-shader" guess). |
| `merge_11ecfrag` | `chara.dat` | `chara` | One atlas bitmap + adjacent `.dat` delta. |
| `merge_11ecfrag2` | `bg.dat` | `bg` | Two source bitmaps (the `-2`/`-1` halves). |

Key points that inform our design:

- **Argument order**: the merge tool takes the **bitmap (atlas) first, then the
  delta `.dat`** — the inverse of what one might expect. `fragmerge_core.merge(fmt, srcs, dat)`
  keeps that order (sources first, descriptor second).
- **`auto` pairing** is asmodean's "guess paired filenames." Our `_resolve_auto`
  and the extraction sidecars reproduce it: a chara descriptor's atlas is the
  adjacent lower-index PNG; a bg descriptor's sources are `idx-2`/`idx-1`.
- **"Extracting everything consumes a lot of space"** is literal — `chara.dat`
  is ~1.1 GB and yields thousands of PNG atlases plus raw `.bin` deltas. The
  original xbdecompress pipeline dropped the `.stream` deltas; we keep both the
  atlases and the deltas (with sidecars) so reassembly works end-to-end.

## chara

- 32×32 source blocks, **1px border trimmed** each side → 30×30 output.
- In `chara.dat` the atlas (PNG) and its descriptor (`.bin`) are **adjacent
  members**: even index = PNG atlas, odd index = `.bin` descriptor. So a
  descriptor `file_NNNN.bin`'s source is `file_NNNN-1.png` (the previous
  member). The sidecar records this automatically; `Open (auto)` / `Open
  folder` resolve it for you.
- Reference unpacker: `crosslnk4/extra-scripts/unpack-11eyes-x360-image.py`
  (atlas `.png` + tilemap `.bin`, 32px blocks / 30px out, `255,255` = skip).

## bg

- 16×16 source blocks, **no trim**.
- Two source halves: the descriptor at index `i` uses `file_(i-2).png` and
  `file_(i-1).png` (the `-2`/`-1` halves of the background).

## 5pb (Xbox 360 / MAGES, LNK4)

- 32×32 blocks, no trim.
- Descriptor is big-endian: header `[u32 entry1_count][u32 entry2_count]`,
  then `entry1` records (`[u16 u16 u32 u32]`) indexing into a pool of
  `entry2` float quads `[f32 dst_x][f32 dst_y][f32 src_x][f32 src_y]`.
- Source coordinates are **floats**: `src_x *= 2048` (then `-1`), and
  `src_y` is scaled by the atlas height (`256/512/1024/2048`, picked from
  `src_h`). `dst` is screen-centered (can be negative); the canvas is sized
  from the min/max `dst`.

## sg (Steins;Gate PC / MAGES engine, MPK)

The PC releases (Steins;Gate Steam, S;G0, Chaos;Child, …) do **not** use LNK4
or Xbox compression. Sprites ship inside an **MPK** container (a simple
little-endian archive; individual files may be zlib-compressed, flagged
per-entry). After unpacking
`chara.mpk`, each sprite is a pair:

- `NAME.png` — the source atlas (all 32×32 chunks concatenated).
- `NAME_.lay` — the descriptor (the trailing `_` is dropped from the atlas
  stem, so `CRS_ALA_.lay` pairs with `CRS_ALA.png`).

The `.lay` layout (per AbsurdlySuspicious/sg-sprite's `lay-format.md`):

```
[u32 sprite_count][u32 chunk_count]
sprite entries (12B): [u8 A][u8 B][u8 C][u8 D][u32 chunk_off][u32 chunk_count]
chunk entries  (16B): [f32 dst_x][f32 dst_y][f32 src_x][f32 src_y]   # then trailing junk
```

`D` is a sprite-type nibble forming a **dependence chain**:

- `0x00` base — drawn first
- `0x20` sub (e.g. a face) — depends on the base
- `0x30`/`0x40`/`0x60` dep (e.g. a mouth) — depends on the sub whose id is `B`
- `0x50` overlay — blended on top (significant alpha)

Chunks are 32×32 blocks; `src` points at pixel `[1,1]` so the tool subtracts 1,
`dst` is the block's upper-left corner in a screen-centered coordinate space
(can be negative — the canvas is sized from the min/max `dst`). Our `merge`
composites a chosen sprite **plus its dependency chain** (base → sub → dep),
and draws overlays with alpha blending. `reconstruct-all` therefore emits one
standalone PNG per sprite entry (`NAME_/NAME__frag_MMM/frag_MMM.png`), each
equal to `merge(..., enabled={i})`.

## LNK4 container & extraction

Each LNK4 member is classified by its **4-byte magic**:

| Member | Output |
|--------|--------|
| `0FF512EE` (LZXNATIVE) → decompresses to a TIMG | `file_NNNN.png` (atlas) |
| `0FF512EE` → decompresses to a non-TIMG (a merge descriptor) | `file_NNNN.bin` + sidecar |
| raw PNG (`89504E47`) | `file_NNNN.png` |
| any other raw member (descriptor) | `file_NNNN.bin` + sidecar |

**Do not** apply the TIMG `depth != 0` heuristic to raw members — chara
descriptors are raw members whose bytes look like a TIMG, which previously
made the extractor call `Image.frombuffer` on them and crash ("not enough
image data") on the fragmented descriptors.

## Alpha handling

The Xbox 360 TIMG atlases store **straight (non-premultiplied) alpha** — the RGB
is the true colour and the alpha channel is separate coverage. `lnk4_extract.py`
and `lnk4_extract_xcompress.py` therefore write the decoded TIMG through to PNG
unchanged (`_timg_to_png`).

Do **not** "un-premultiply" these atlases. Dividing the RGB by `alpha/255` is
wrong for straight-alpha data: a semi-transparent edge pixel whose stored RGB is
a normal (bright) colour would be inflated far above 255 and clip to white,
leaving a white halo/fringe around sprites. This was a real bug.

The Steins;Gate PC (`sg`) atlases are ordinary PNG and likewise straight alpha.

## Sidecar files

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
