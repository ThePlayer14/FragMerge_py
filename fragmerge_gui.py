"""fragmerge_gui.py

PySide6 viewer for asmodean's "merge_*frag" slice-reassembly tools.

Loads the source image(s) + descriptor (.dat), reassembles the sliced
image in memory ("undoing the slicing"), shows a preview, lets you toggle
individual fragments on/off, and saves the result to PNG/BMP when wanted.

The layout lives in ``fragmerge_gui.ui`` (edit with Qt Designer, then
regenerate the binding with::

    pyside6-uic fragmerge_gui.ui -o fragmerge_gui_ui.py

so the changes are picked up on the next run).  The left side is a tabbed
panel (Merge / Debug); the right side is always the live preview.

Usage:
    python3 fragmerge_gui.py
"""

from __future__ import annotations

import glob
import os
import re
import struct
import threading

import numpy as np
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QListWidgetItem, QMainWindow,
    QMessageBox,
)

from fragmerge_gui_ui import Ui_FragMergeApp
import fragmerge_core as fm

MAX_PREVIEW = 1000  # longest preview edge in px


class MergeWorker(QThread):
    """Runs fm.merge off the GUI thread."""

    done = Signal(object, int, bool)   # arr, n, had_list
    error = Signal(object)             # exception

    def __init__(self, fmt, srcs, dat, enabled, scale_override):
        super().__init__()
        self.fmt = fmt
        self.srcs = srcs
        self.dat = dat
        self.enabled = enabled
        self.scale_override = scale_override

    def run(self) -> None:
        try:
            arr, n = fm.merge(self.fmt, self.srcs, self.dat,
                              enabled=self.enabled,
                              scale_override=self.scale_override)
            self.done.emit(arr, n, bool(self.enabled is not None))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(exc)


class FragMergeApp(QMainWindow, Ui_FragMergeApp):
    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)

        self.fmt = "chara"
        self.src1_path = self.src2_path = self.dat_path = ""
        self.scale_str = "auto"  # 5pb src-y scale

        self.merged: np.ndarray | None = None
        self.frag_count = 0
        self.enabled: set[int] = set()
        self._frag_checks: list = []
        self._busy = False
        self._worker: MergeWorker | None = None
        self._folder: str | None = None
        self._zoom: float | None = None  # None = fit-to-view
        self._zoom_base: tuple[int, int] = (0, 0)  # current image w,h
        self.white_bg: bool = False      # composite preview over white

        self._wire()

    # ------------------------------------------------------------------ wiring
    def _wire(self) -> None:
        # Format radios
        self.radioChara.toggled.connect(lambda c: self._on_fmt_radio("chara", c))
        self.radioBg.toggled.connect(lambda c: self._on_fmt_radio("bg", c))
        self.radio5pb.toggled.connect(lambda c: self._on_fmt_radio("5pb", c))
        self.radioSg.toggled.connect(lambda c: self._on_fmt_radio("sg", c))

        # File pickers
        self.btnSrc1.clicked.connect(lambda: self._pick("src1"))
        self.btnSrc2.clicked.connect(lambda: self._pick("src2"))
        self.btnDat.clicked.connect(lambda: self._pick("dat"))

        # Open helpers
        self.btnOpenAuto.clicked.connect(self._open_auto)
        self.btnOpenFolder.clicked.connect(self._open_folder)

        # Scale entry
        self.scaleEntry.textChanged.connect(
            lambda t: setattr(self, "scale_str", t))

        # Descriptor list
        self.descriptorList.itemDoubleClicked.connect(self._on_list_item)
        self.descriptorList.currentItemChanged.connect(self._on_list_item)

        # Actions
        self.btnPreview.clicked.connect(self._preview)
        self.btnSave.clicked.connect(self._save)
        self.btnFragAll.clicked.connect(lambda: self._set_all(True))
        self.btnFragNone.clicked.connect(lambda: self._set_all(False))

        # Zoom controls
        self.btnZoomIn.clicked.connect(lambda: self._zoom_by(1.25))
        self.btnZoomOut.clicked.connect(lambda: self._zoom_by(1 / 1.25))
        self.btnZoomReset.clicked.connect(self._zoom_reset)
        self.whiteBgCheck.toggled.connect(self._on_white_bg)

        # Debug tab
        self.btnDumpSlices.clicked.connect(self._dump_slices)
        self.btnDumpImages.clicked.connect(self._dump_slice_images)
        self.btnDumpAllDir.clicked.connect(
            lambda: self._browse_dir(self.dumpAllDir))
        self.btnDumpAllOut.clicked.connect(
            lambda: self._browse_dir(self.dumpAllOut))
        self.btnDumpAllRun.clicked.connect(self._dump_all)

        # Reconstruct fragments (Debug tab)
        self.btnReconDir.clicked.connect(
            lambda: self._browse_dir(self.reconDir))
        self.btnReconOut.clicked.connect(
            lambda: self._browse_dir(self.reconOut))
        self.btnReconRun.clicked.connect(self._reconstruct_all)

        self._on_fmt()

    def _on_fmt_radio(self, name: str, checked: bool) -> None:
        if checked:
            self.fmt = name
            self._on_fmt()

    def _on_fmt(self) -> None:
        is_bg = self.fmt == "bg"
        is_5pb = self.fmt == "5pb"
        self.btnSrc2.setVisible(is_bg)
        self.src2Label.setVisible(is_bg)
        self.scaleLabel.setVisible(is_5pb)
        self.scaleEntry.setVisible(is_5pb)
        self.scaleHint.setVisible(is_5pb)

    def _pick(self, which: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose file", "",
            "Images (*.png *.bmp);;DAT (*.dat);;All (*.*)")
        if not path:
            return
        if which == "src1":
            self.src1_path = path
            self.src1Label.setText(path)
        elif which == "src2":
            self.src2_path = path
            self.src2Label.setText(path)
        else:
            self.dat_path = path
            self.datLabel.setText(path)

    def _browse_dir(self, line_edit) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose folder")
        if d:
            line_edit.setText(d)

    # --------------------------------------------------- auto-resolve
    def _resolve_auto(self, path: str):
        """Given one file from an extracted LNK4 folder, resolve the
        (format, source_paths, descriptor_path) triple, or None if the
        needed files are missing."""
        folder = os.path.dirname(path) or "."
        base = os.path.basename(path)

        if base.lower().endswith(".lay"):
            # MAGES .lay: resolved entirely by base-name pairing below.
            dat = path
        elif base.lower().endswith(".bin"):
            dat = path
            idx = int(os.path.splitext(base)[0].split("_")[1])
        elif self.fmt == "sg" and base.lower().endswith(".png"):
            # MAGES atlas PNG: find the paired .lay by base-name.
            stem = os.path.splitext(base)[0]
            cands = [stem + "_.lay", stem + ".lay"]
            dat = next((os.path.join(folder, c)
                        for c in cands if os.path.exists(os.path.join(folder, c))), None)
            if dat is None:
                return None
            return self.fmt, [path], dat
        else:
            m = re.search(r"_(\d+)\.", base)
            if not m:
                return None
            idx = int(m.group(1))
            dat = None  # resolved per-format below

        if self.fmt == "bg":
            if dat is None:
                dat = os.path.join(folder, "file_%04d.bin" % idx)
            s1 = os.path.join(folder, "file_%04d.png" % (idx - 2))
            s2 = os.path.join(folder, "file_%04d.png" % (idx - 1))
            if not (os.path.exists(s1) and os.path.exists(s2)):
                return None
            return self.fmt, [s1, s2], dat

        if self.fmt == "chara":
            # Atlas (PNG) and descriptor (.bin) are adjacent members: the
            # atlas precedes the descriptor.  So a descriptor at `idx` uses
            # `idx-1`; an atlas at `idx` uses `idx+1`.  Accept either.
            dat_is_bin = base.lower().endswith(".bin")
            if dat_is_bin:
                dat = path
                s1 = os.path.join(folder, "file_%04d.png" % (idx - 1))
                if not os.path.exists(s1):
                    s1 = os.path.join(folder, "file_%04d.png" % (idx + 1))
            else:
                s1 = os.path.join(folder, "file_%04d.png" % idx)
                dat = os.path.join(folder, "file_%04d.bin" % (idx + 1))
                if not os.path.exists(dat):
                    dat = os.path.join(folder, "file_%04d.bin" % (idx - 1))
            if not (os.path.exists(s1) and os.path.exists(dat)):
                return None
            return self.fmt, [s1], dat

        if self.fmt == "sg":
            # MAGES .lay + .png: both in the same folder, base names related.
            # e.g. CRS_ALA_.lay  <->  CRS_ALA.png  (trailing '_' stripped).
            if base.lower().endswith(".lay"):
                dat = path
                stem = os.path.splitext(base)[0]
                if stem.endswith("_"):
                    stem = stem[:-1]
                cands = [stem + ".png", stem + "_.png",
                         os.path.splitext(base)[0] + ".png"]
                s1 = next((c for c in cands
                           if os.path.exists(os.path.join(folder, c))), None)
                if s1 is None:
                    return None
                return self.fmt, [os.path.join(folder, s1)], dat
            # Given a .png: find the matching .lay (base stem may carry a
            # trailing '_' that the atlas drops, e.g. CRS_ALA.png <-> CRS_ALA_.lay).
            stem = os.path.splitext(base)[0]
            cands = [stem + "_.lay", stem + ".lay", stem + "_" + ".lay"]
            dat = next((os.path.join(folder, c)
                        for c in cands if os.path.exists(os.path.join(folder, c))), None)
            if dat is None:
                return None
            return self.fmt, [path], dat

        s1 = os.path.join(folder, "file_%04d.png" % idx)
        if not os.path.exists(s1):
            return None
        return self.fmt, [s1], dat

    def _open_auto(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open", "",
            "PNG (*.png);;Descriptor (*.bin);;LNK4 container (*.dat);;All (*.*)")
        if not path:
            return
        if os.path.splitext(path)[1].lower() == ".dat":
            self._open_container(path)
            return
        res = self._resolve_auto(path)
        if res is None:
            _info(self, "Cannot auto-load",
                  "Pick a file_NNNN.png or file_NNNN.bin from an extracted "
                  "LNK4 folder (or an LNK4 .dat container). For 'bg', the "
                  "-2/-1 source PNGs must exist.")
            return
        self._apply_resolved(res)

    def _open_container(self, container: str) -> None:
        import tempfile
        out = tempfile.mkdtemp(prefix="fragmerge_")
        self.statusLabel.setText("Extracting %s …" % os.path.basename(container))
        self.btnPreview.setEnabled(False)

        def worker() -> None:
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "lnk4_extract",
                    os.path.join(os.path.dirname(__file__), "lnk4_extract.py"))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.extract_lnk4(container, out, workers=(os.cpu_count() or 1))
                self._after_extract(container, out)
            except Exception as exc:  # noqa: BLE001
                _err(self, "Extract failed", str(exc))
            finally:
                self.btnPreview.setEnabled(True)

        threading.Thread(target=worker, daemon=True).start()

    def _after_extract(self, container: str, out: str) -> None:
        bins = sorted(glob.glob(os.path.join(out, "*.bin")))
        if not bins:
            _info(self, "Nothing to load",
                  "No descriptors (.bin) found after extraction.")
            return
        res = self._resolve_auto(bins[0])
        if res is None:
            _info(self, "Cannot auto-load",
                  "Extracted, but source PNGs for %s are missing."
                  % os.path.basename(bins[0]))
            return
        self._apply_resolved(res)
        self.statusLabel.setText("Extracted %s -> %s (showing %s)" %
                                 (os.path.basename(container), out,
                                  os.path.basename(res[2])))

    def _apply_resolved(self, res) -> None:
        fmt, srcs, dat = res
        self.fmt = fmt
        self.radioChara.setChecked(fmt == "chara")
        self.radioBg.setChecked(fmt == "bg")
        self.radio5pb.setChecked(fmt == "5pb")
        self._on_fmt()

        self.src1_path = srcs[0]
        self.src1Label.setText(srcs[0])
        if fmt == "bg" and len(srcs) > 1:
            self.src2_path = srcs[1]
            self.src2Label.setText(srcs[1])
        self.dat_path = dat
        self.datLabel.setText(dat)
        self._frag_checks = []  # fresh fragment list for the new file
        self._preview()

    # --------------------------------------------------- folder / sidecars
    def _open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open extracted LNK4 folder")
        if not folder:
            return
        self._folder = folder
        sidecars = sorted(glob.glob(os.path.join(folder, "file_*.json")))
        self.descriptorList.clear()
        if not sidecars:
            self.listInfoLabel.setText(
                "No descriptor sidecars (*.json) found in %s.\n"
                "Extract with lnk4_extract first, or use 'Open' to "
                "auto-resolve by naming convention." % folder)
            return
        for sc_path in sidecars:
            sc = fm.read_extract_sidecar(sc_path)
            idx = sc.get("index", -1)
            sources = sc.get("sources", {})
            n_src = len(sources.get("bg", [])) or len(sources.get("single", []))
            have = "src ok" if n_src else "NO SOURCES"
            item = QListWidgetItem("file_%04d.bin  (%s)" % (idx, have))
            item.setData(Qt.ItemDataRole.UserRole, sc_path)
            self.descriptorList.addItem(item)
        self.listInfoLabel.setText(
            "%d descriptors in %s. Click one to load (format = current "
            "radio). Descriptors with sources are ready to merge." % (
                len(sidecars), os.path.basename(folder)))

    def _on_list_item(self, item: QListWidgetItem) -> None:
        if item is None:
            return
        sc_path = item.data(Qt.ItemDataRole.UserRole)
        if not sc_path:
            return
        sc = fm.read_extract_sidecar(sc_path)
        folder = os.path.dirname(sc_path)
        res = self._resolve_from_sidecar(sc, folder)
        if res is None:
            _info(self, "Cannot auto-load",
                  "Descriptor %s has no matching source images for format "
                  "'%s'. Switch the format radio and click again." % (
                      sc.get("descriptor", "?"), self.fmt))
            return
        self._apply_resolved(res)

    def _resolve_from_sidecar(self, sc: dict, folder: str):
        """Resolve (fmt, srcs, dat) for the current format radio, or None."""
        dat = os.path.join(folder, sc.get("descriptor", ""))
        if not os.path.exists(dat):
            return None
        srcs = fm.sidecar_sources(sc, self.fmt, folder)
        if self.fmt == "bg":
            if len(srcs) != 2 or not all(os.path.exists(s) for s in srcs):
                return None
        else:
            if len(srcs) != 1 or not os.path.exists(srcs[0]):
                return None
        return self.fmt, srcs, dat

    # -------------------------------------------------------------- actions
    def _src_paths(self) -> list[str]:
        paths = [self.src1_path]
        if self.fmt == "bg":
            paths.append(self.src2_path)
        return paths

    def _build_frag_list(self) -> None:
        for w in self.fragInnerWidget.findChildren(QCheckBox):
            w.deleteLater()
        self._frag_checks = []
        self.enabled = set(range(self.frag_count))
        for i in range(self.frag_count):
            cb = QCheckBox("fragment %03d" % i)
            cb.setChecked(True)
            cb.toggled.connect(self._preview)
            self.fragListLayout.addWidget(cb)
            self._frag_checks.append(cb)

    def _enabled_set(self) -> set[int]:
        return {i for i, c in enumerate(self._frag_checks) if c.isChecked()}

    def _set_all(self, val: bool) -> None:
        for c in self._frag_checks:
            c.setChecked(val)
        self._preview()

    def _preview(self) -> None:
        if self._busy:
            return
        srcs = self._src_paths()
        dat = self.dat_path
        if not dat or not all(srcs) or (self.fmt == "bg" and not self.src2_path):
            self.statusLabel.setText(
                "Need source image(s) + .dat for format '%s'." % self.fmt)
            return

        scale = None
        if self.fmt == "5pb":
            s = self.scale_str.strip().lower()
            if s and s != "auto":
                scale = int(s)
        enabled = self._enabled_set() if self._frag_checks else None
        have_list = bool(self._frag_checks)

        self._busy = True
        self.btnPreview.setEnabled(False)
        self.statusLabel.setText("Loading %s …" % os.path.basename(dat))

        self._worker = MergeWorker(self.fmt, srcs, dat, enabled, scale)
        self._worker.done.connect(
            lambda arr, n, hl: self._preview_done(arr, n, hl))
        self._worker.error.connect(self._preview_error)
        self._worker.start()

    def _preview_done(self, arr: np.ndarray, n: int, had_list: bool) -> None:
        self._busy = False
        self.btnPreview.setEnabled(True)
        if not had_list:
            self.frag_count = n
            self._build_frag_list()
        self.merged = arr
        self._show(arr)
        self.statusLabel.setText(
            "%s: %d fragments, %dx%d — preview (not yet saved)" %
            (self.fmt, n, arr.shape[1], arr.shape[0]))

    def _preview_error(self, exc: Exception) -> None:
        self._busy = False
        self.btnPreview.setEnabled(True)
        _err(self, "Merge failed", str(exc))
        self.statusLabel.setText("Error: %s" % exc)

    def _show(self, arr: np.ndarray) -> None:
        self.merged = arr
        h, w = arr.shape[:2]
        self._zoom_base = (w, h)
        if self._zoom is None:
            self._render_zoom()
        else:
            self._render_zoom()

    def _fit_scale(self) -> float:
        w, h = self._zoom_base
        if not w or not h:
            return 1.0
        return min(1.0, MAX_PREVIEW / max(w, h))

    def _effective_zoom(self) -> float:
        fit = self._fit_scale()
        return fit if self._zoom is None else self._zoom * fit

    def _on_white_bg(self, checked: bool) -> None:
        self.white_bg = checked
        self._render_zoom()

    def _render_zoom(self) -> None:
        if self.merged is None:
            return
        arr = self.merged
        h, w = arr.shape[:2]
        if self.white_bg:
            # Composite straight-alpha RGBA over opaque white for preview.
            rgba = arr.astype(np.float32) / 255.0
            a = rgba[:, :, 3:4]
            rgb = rgba[:, :, :3] * a + (1.0 - a)
            disp = (np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
            qimg = QImage(disp.tobytes(), w, h, w * 3, QImage.Format.Format_RGB888)
        else:
            qimg = QImage(arr.tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888)
        pix = QPixmap.fromImage(qimg)
        z = self._effective_zoom()
        if z != 1.0:
            pix = pix.scaled(int(w * z), int(h * z),
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        self.canvasLabel.setPixmap(pix)
        self.canvasLabel.resize(pix.size())
        pct = int(round(z * 100))
        self.zoomLabel.setText("fit" if self._zoom is None else "%d%%" % pct)

    def _zoom_by(self, factor: float) -> None:
        fit = self._fit_scale()
        # Maintain an absolute zoom factor (relative to 1:1 image), initialized
        # from the current effective zoom when leaving fit mode.
        if self._zoom is None:
            self._zoom = self._effective_zoom()
        self._zoom = max(0.05, min(16.0, self._zoom * factor))
        self._render_zoom()

    def _zoom_reset(self) -> None:
        self._zoom = None
        self._render_zoom()

    def _save(self) -> None:
        if self.merged is None:
            _info(self, "Nothing to save", "Run Preview first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save image", "", "PNG (*.png);;BMP (*.bmp)")
        if not path:
            return
        fm.save_rgba(self.merged, path)
        self.statusLabel.setText("Saved %s (%dx%d)" %
                                 (os.path.basename(path), self.merged.shape[1],
                                  self.merged.shape[0]))

    def _dump_slices(self) -> None:
        if not self.dat_path:
            _info(self, "No descriptor", "Load a .dat file first.")
            return
        txt = fm.dump_slices(self.fmt, self.dat_path)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save slice dump", "", "Text (*.txt);;All (*.*)")
        if not path:
            return
        with open(path, "w") as f:
            f.write(txt)
        _info(self, "Done", "Slice grid written to %s" % path)

    def _dump_slice_images(self) -> None:
        if not self.dat_path:
            _info(self, "No descriptor", "Load a .dat file first.")
            return
        srcs = [self.src1_path]
        if self.fmt == "bg":
            if not self.src2_path:
                _info(self, "Missing source 2", "bg format requires both source images.")
                return
            srcs.append(self.src2_path)
        out_dir = QFileDialog.getExistingDirectory(self, "Output directory for slice strips")
        if not out_dir:
            return
        try:
            res = fm.dump_slices_images(self.fmt, srcs, self.dat_path, out_dir)
            _info(self, "Done",
                  "Extracted %d strips to %s\nManifest: %s" %
                  (len(res["strips"]), out_dir, res["manifest_path"]))
        except Exception as exc:  # noqa: BLE001
            _err(self, "Dump failed", str(exc))

    def _dump_all(self) -> None:
        extract_dir = self.dumpAllDir.text().strip()
        out_dir = self.dumpAllOut.text().strip()
        fmt = self.dumpAllFmt.currentText()
        workers = self.dumpAllWorkers.value()
        if not extract_dir or not os.path.isdir(extract_dir):
            _info(self, "Missing input", "Choose an extraction folder first.")
            return
        if not out_dir:
            _info(self, "Missing output", "Choose an output folder first.")
            return
        from concurrent.futures import ThreadPoolExecutor
        try:
            bins = sorted(glob.glob(os.path.join(extract_dir, "*.bin")))
            if fmt == "sg":
                bins = sorted(glob.glob(os.path.join(extract_dir, "*.lay")))
            total = 0
            for b in bins:
                base = os.path.basename(b)
                if fmt == "sg":
                    atl = self._sg_atlas_for_lay(b)
                    if atl is None:
                        self.statusLabel.setText("skip %s: missing atlas" % base)
                        QApplication.processEvents()
                        continue
                    srcs = [atl]
                    idx_tag = os.path.splitext(base)[0]  # keep .lay stem as folder
                else:
                    idx = int(base.split("_")[1].split(".")[0])
                    if fmt == "bg":
                        s1 = os.path.join(extract_dir, "file_%04d.png" % (idx - 2))
                        s2 = os.path.join(extract_dir, "file_%04d.png" % (idx - 1))
                        if not (os.path.exists(s1) and os.path.exists(s2)):
                            self.statusLabel.setText("skip %s: missing sources" % base)
                            QApplication.processEvents()
                            continue
                        srcs = [s1, s2]
                    else:
                        s1 = os.path.join(extract_dir, "file_%04d.png" % idx)
                        if not os.path.exists(s1):
                            self.statusLabel.setText("skip %s: missing source" % base)
                            QApplication.processEvents()
                            continue
                        srcs = [s1]
                    idx_tag = "file_%04d" % idx
                with open(b, "rb") as f:
                    dat = f.read()
                frag_count = self._descriptor_frag_count(fmt, dat)
                desc_folder = os.path.join(out_dir, idx_tag)
                os.makedirs(desc_folder, exist_ok=True)

                # Fragment dumps for one descriptor are independent; run them
                # in a pool so multi-fragment descriptors (chara) finish faster.
                def _dump_frag(fi: int) -> int:
                    frag_dir = os.path.join(desc_folder, "%s_frag_%03d" % (idx_tag, fi))
                    res = fm.dump_slices_images(
                        fmt, srcs, b, frag_dir, frag_idx=fi)
                    return len(res["strips"])

                if workers > 1 and frag_count > 1:
                    with ThreadPoolExecutor(max_workers=workers) as ex:
                        for n in ex.map(_dump_frag, range(frag_count)):
                            total += n
                else:
                    for fi in range(frag_count):
                        total += _dump_frag(fi)
                self.statusLabel.setText("  %s: %d fragments done" % (base, frag_count))
                QApplication.processEvents()
            _info(self, "Done", "Total %d strips -> %s" % (total, out_dir))
        except Exception as exc:  # noqa: BLE001
            _err(self, "Batch dump failed", str(exc))

    @staticmethod
    def _descriptor_index(path: str) -> int | None:
        base = os.path.splitext(os.path.basename(path))[0]
        if not base.startswith("file_"):
            return None
        try:
            return int(base.split("_")[1])
        except (IndexError, ValueError):
            return None

    def _reconstruct_all(self) -> None:
        extract_dir = self.reconDir.text().strip()
        out_dir = self.reconOut.text().strip()
        fmt = self.reconFmt.currentText()
        workers = self.reconWorkers.value()
        if not extract_dir or not os.path.isdir(extract_dir):
            _info(self, "Missing input", "Choose an extraction folder first.")
            return
        if not out_dir:
            _info(self, "Missing output", "Choose an output folder first.")
            return
        from concurrent.futures import ThreadPoolExecutor
        try:
            bins = sorted(glob.glob(os.path.join(extract_dir, "*.bin")))
            if fmt == "sg":
                bins = sorted(glob.glob(os.path.join(extract_dir, "*.lay")))

            def _recon_one(b: str) -> int:
                if fmt == "sg":
                    atl = self._sg_atlas_for_lay(b)
                    if atl is None:
                        return 0
                    srcs = [atl]
                else:
                    idx = self._descriptor_index(b)
                    if idx is None:
                        return 0
                    if fmt == "bg":
                        s1 = os.path.join(extract_dir, "file_%04d.png" % (idx - 2))
                        s2 = os.path.join(extract_dir, "file_%04d.png" % (idx - 1))
                        if not (os.path.exists(s1) and os.path.exists(s2)):
                            return 0
                        srcs = [s1, s2]
                    else:
                        s1 = os.path.join(extract_dir, "file_%04d.png" % idx)
                        if not os.path.exists(s1):
                            return 0
                        srcs = [s1]
                res = fm.reconstruct_fragments(fmt, srcs, b, out_dir)
                return res["fragment_count"]

            total = 0
            if workers > 1 and len(bins) > 1:
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    for n in ex.map(_recon_one, bins):
                        total += n
                        self.statusLabel.setText("... %d fragments reconstructed" % total)
                        QApplication.processEvents()
            else:
                for b in bins:
                    n = _recon_one(b)
                    total += n
                    self.statusLabel.setText("... %d fragments reconstructed" % total)
                    QApplication.processEvents()
            _info(self, "Done", "Total %d reconstructed fragments -> %s" % (total, out_dir))
        except Exception as exc:  # noqa: BLE001
            _err(self, "Reconstruct failed", str(exc))

    @staticmethod
    def _sg_atlas_for_lay(lay_path: str) -> str | None:
        """Find the atlas PNG paired with a MAGES ``.lay`` descriptor."""
        folder = os.path.dirname(lay_path) or "."
        stem = os.path.splitext(os.path.basename(lay_path))[0]
        if stem.endswith("_"):
            stem = stem[:-1]
        for c in (stem + ".png", stem + "_.png",
                  os.path.splitext(os.path.basename(lay_path))[0] + ".png"):
            p = os.path.join(folder, c)
            if os.path.exists(p):
                return p
        return None

    @staticmethod
    def _descriptor_frag_count(fmt: str, dat: bytes) -> int:
        if fmt == "bg":
            w0, h0 = struct.unpack_from("<2H", dat, 0)
            p = 4 + w0 * h0 * 2
            return 1 + struct.unpack_from("<H", dat, p)[0]
        if fmt == "chara":
            return struct.unpack_from("<6H I", dat, 0)[0]
        return struct.unpack_from(">2I", dat, 0)[0]


# --------------------------------------------------------------- helpers
def _info(parent, title, msg):
    QMessageBox.information(parent, title, msg)


def _err(parent, title, msg):
    QMessageBox.critical(parent, title, msg)


def main() -> None:
    app = QApplication([])
    win = FragMergeApp()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
