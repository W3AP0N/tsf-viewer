from tsf_converter import convert_tsf_to_h5
import ftp_service

import os
import io
import re
import sys
import csv
import uuid
import time
import h5py
import gzip
import base64
import ctypes
import signal
import tomllib
import requests
import platform
import warnings
import threading
import traceback
import numpy as np
import pandas as pd
import pyqtgraph as pg
from pyqtgraph import Point
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSizePolicy,
    QTextBrowser,
)
from PyQt6.QtCore import Qt, QEvent
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon

os.chdir(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)))

# =====================================================
# Globális hibakezelés
# =====================================================
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Globális hibakezelő: elkap minden kezeletlen kivételt a programban,
    kiírja a hiba részleteit, majd várakozik egy gombnyomásra kilépés előtt.
    """
    # A Ctrl+C (KeyboardInterrupt) megszakítást hagyjuk simán lefutni
    if issubclass(exc_type, KeyboardInterrupt):
        os._exit(0)  # Kényszerített, azonnali kilépés

    print("\n" + "=" * 60)
    print("CRITICAL ERROR:")
    print("=" * 60)
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print("=" * 60)
    input("\n\nPress ENTER to exit...")

# CTRL + C egyből leáll a program
def sigint_handler(signal_received, frame):
    print()
    os._exit(0)

sys.excepthook = global_exception_handler
signal.signal(signal.SIGINT, sigint_handler)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyqtgraph")

# =====================================================
# Config fájl betöltése
# =====================================================
if os.path.exists("config.toml"):
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
else:
    print("[INFO] 'config.toml' is missing")

    DEFAULT_CONFIG_GZIP = "H4sIANzlgmoC/4VUPW/bMBDd9SsOztICieEiKVAU6JCiSduhS9uhQFAYlHyWKVKkQJ6VSP+gY36CRw0ZigAeim5E/lePkh27H3A1UeTp3XvvHnVVaUtfkyM4hzysXRo6AyXmBWo0D7fg27CuMUcFZegcEh5DRScpmniyKq2uRfxWi4qPCXWJLRJBfAmdegnPJsncGpp62SK8iq+7Vgi1NYIRPInch1V+GOo00dLg9FrOaMFQpwPSHLVnnl+A0OSoG2amQ1fzFnpkzqZhKWGtH24fJRwmfJpgjcy4FE6heyS+bcdQM8etQudByUoQCRNWnmDbBqqwJmqiP3cGIdbt9R22o8NithAU7h8d9n3pAm/EDDNZhpWWHubW8YqWZSoMSM8IlR7DqEGt7fUIapE3MDq65GcyGR3QhaxslDXCjPouLxKbZUvHOjLcCs2sto6VDmX/KNg48SJJrlj2YshM5WzuRAnzJbELYbWwbVT0U/nQRU3zsCq0VcDmdI5bSwg/qBAy+R/ZmWDVVo3phgbOozlV48JbE3VepDGCoo1Dpn4ZmRSoCFRYm6ZmNi56xsTRe+bDFRsugsbJBn3K6FHyfrOE+0xjn3iw65lcZbasIpi0ptfOzY0JnQbDU7BpCp8/Xe56DIx6b969uXy+P0mgsC75AoQ7kmNGCt/cDEs2i09QF7z4eP5hExoOMN+9ebSPhtQYeQxvX8OTXOYilYRPfwtJxLtoUWEkkEqOpuMYcZi05RrT9NS8VUpoYNbOizTaFO+x9/wF7ngfMxS2cSa8lzdCOdEH1zSSLE9rJ5VrBgE7YWjkmOOhOdh541t0D9/TlAHLcD8rRHQO+5FIjX2wplqWMs5isk2B49+D0HxBInlG5HiJMbyPN1xxUDlwJOImg8bsmT3DxZJsKUiqpR8oq55hy84tLN8YFe5q/qJYqhP8g3Ny8OdwlvxN+Cz5BaFX6PJDBQAA".strip()

    answer = input("[INFO] Would you like to create one? [Y/n]: ")

    if answer.lower() in ("y", "yes", ""):
        config_text = gzip.decompress(
            base64.b64decode(DEFAULT_CONFIG_GZIP)
        ).decode("utf-8")

        with open("config.toml", "w", encoding="utf-8") as f:
            f.write(config_text)

        print("[INFO] 'config.toml' has been created\n")

        with open("config.toml", "rb") as f:
            config = tomllib.load(f)
    else:
        print()
        config = {}

plot_config = config.get("plot", {})
font_size = plot_config.get("font_size", 10)
line_width = plot_config.get("line_width", 3)
event_marker_size = plot_config.get("event_marker_size", 13)
occurrence_marker_color = plot_config.get("occurrence_marker_color", "cyan")
occurrence_marker_size = plot_config.get("occurrence_marker_size", 8)

path_config = config.get("path", {})
datumok_txt = path_config.get("datumok_txt", "datumok.txt")
ftp_json = path_config.get("ftp_json", "ftp.json")

compression_config = config.get("compression", {})
file_size_limit = compression_config.get("file_size_limit", 4)

# =====================================================
# Argumentumok kezelése és inicializálás
# =====================================================
is_win = platform.system() == "Windows"
#is_win = True
exec_cmd = r".\TSF_Viewer.exe" if is_win else "./tsf_viewer"

if len(sys.argv) < 2:
    print("Usage:")
    print(f"   {exec_cmd} <file.tsf> [file.earthquake.tsf]")
    print("   You can use relative and absolute file paths")
    if is_win:
        print("   Or drop a file on the .exe")

    input("\n\nPress ENTER to exit...")
    sys.exit(1)

if is_win:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tsf-viewer.1.0")
    except Exception:
        pass

filepath = sys.argv[1]
filename = os.path.basename(filepath)
base_name, _ = os.path.splitext(filename)

is_h5 = False

if not os.path.isfile(filepath):
    print(f"ERROR: File does not exist '{filepath}'")
    input("\n\nPress ENTER to exit...")
    sys.exit(1)

if not filename.lower().endswith((".tsf", ".tsf.h5")):
    print(f"ERROR: '{filename}' is not a valid .tsf file!")
    input("\n\nPress ENTER to exit...")
    sys.exit(1)

if len(sys.argv) >= 3:
    filepath2 = sys.argv[2]
    if not filepath2.endswith(".earthquake.tsf"):
        print(f"ERROR: '{os.path.basename(filepath2)}' is not a .earthquake.tsf file!")
        input("\n\nPress ENTER to exit...")
        sys.exit(1)

parts = base_name.split("_")
station = parts[0].upper() if len(parts) > 0 else ""
sensor = parts[1].upper() if len(parts) > 1 else ""

if station == "CONRAD":
    station = "COBS"
    sensor = "SOP2"

print(f"Station: {station}")
print(f"Sensor: {sensor}")

if not os.path.exists(datumok_txt):
    print("WARNING: 'datumok.txt' is missing")

if not os.path.exists(ftp_json):
    print("WARNING: 'ftp.json' is missing")

# =====================================================
# Tengely azonosító segédfüggvény
# =====================================================
def get_axis(name):
    if not name:
        return None
    n = name.lower()
    if any(k in n for k in ("x_tilt", "x channel")) or n.startswith("x"):
        return "x"
    if any(k in n for k in ("y_tilt", "y channel")) or n.startswith("y"):
        return "y"
    return None

# =====================================================
# Fájl betöltés
# =====================================================
@contextmanager
def animated_loading(message):
    """Egységes kontextuskezelő a töltési animációhoz és időméréshez."""
    loading_stop = threading.Event()

    def _format_time(seconds: float) -> str:
        """Segédfüggvény az idő formázására (1 perc felett XmYY.YYYs formátum)."""
        if seconds >= 60:
            mins, secs = divmod(seconds, 60)
            return f"{int(mins)}m{secs:06.3f}s"
        return f"{seconds:.3f}s"

    def _animate():
        dots = ("", ".", "..", "...")
        idx = 0
        while not loading_stop.is_set():
            sys.stdout.write(f"\r{message}{dots[idx % 4]:<4}")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.3)

    anim_thread = threading.Thread(target=_animate)
    anim_thread.start()
    start_time = time.time()

    try:
        yield
    except Exception as e:
        elapsed = time.time() - start_time
        loading_stop.set()
        anim_thread.join()
        sys.stdout.write(f"\r{message}... FAILED! ({_format_time(elapsed)})\n")
        sys.stdout.flush()
        raise e
    else:
        elapsed = time.time() - start_time
        loading_stop.set()
        anim_thread.join()
        sys.stdout.write(f"\r{message}... Done! ({_format_time(elapsed)})\n")
        sys.stdout.flush()

_OPEN_H5_FILES = {}

def load_tsf(path, handle_gaps=False, replace_9999=False, size_limit_gb=file_size_limit):
    f_name = os.path.basename(path)
    global is_h5

    # =========================================================================
    # 0. KÖZVETLEN HDF5 (.h5 / .tsf.h5) FÁJL BETÖLTÉSE
    # =========================================================================
    if path.endswith(".tsf.h5") or path.endswith(".h5"):
        if not os.path.exists(path):
            print(f"ERROR: File does not exist '{path}'")
            return np.array([]), np.empty((0, 0)), [], [], None, []

        try:
            with animated_loading(f"Reading '{f_name}'"):
                h5f = h5py.File(path, "r")
                _OPEN_H5_FILES[path] = h5f

                timestamps = h5f["timestamps"][:]
                data_matrix = h5f["data_matrix"][:]

                raw_channels = h5f.attrs.get("channel_names", [])
                channel_names = [c.decode("utf-8") if isinstance(c, bytes) else str(c) for c in raw_channels]

                raw_units = h5f.attrs.get("units", [])
                units = [u.decode("utf-8") if isinstance(u, bytes) else str(u) for u in raw_units]

                inc_val = h5f.attrs.get("increment", np.nan)
                increment_ret = float(inc_val) if not np.isnan(inc_val) else None

                gaps_ret = list(h5f["gaps"][:]) if "gaps" in h5f else []

        except Exception as e:
            print(f"ERROR while reading HDF5 file: {e}")
            return np.array([]), np.empty((0, 0)), [], [], None, []

        return timestamps, data_matrix, channel_names, units, increment_ret, gaps_ret

    # =========================================================================
    # 0/B. ELLENŐRZÉS: LÉTEZIK-E A PROJEKTMAPPÁBAN A LEGENERÁLT .TSF.H5 VÁLTOZAT?
    # =========================================================================
    h5_in_project = os.path.basename(path) + ".h5"  # pl. "adatok.tsf.h5" a projektmappában

    if os.path.exists(h5_in_project):
        is_h5 = True
        return load_tsf(
            path=h5_in_project,
            handle_gaps=handle_gaps,
            replace_9999=replace_9999,
            size_limit_gb=size_limit_gb
        )

    # =========================================================================
    # 1. FEJLÉC BEOLVASÁSA (NORMÁL .TSF FÁJL ESETÉN)
    # =========================================================================
    channel_names, units = [], []
    increment = None
    data_start_line = 0

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        mode = None
        for line_idx, line in enumerate(f):
            s = line.strip()
            if not s:
                continue
            if s.startswith("[INCREMENT]"):
                try:
                    increment = float(s.split("]", 1)[1].strip())
                except ValueError:
                    increment = None
                continue
            if s == "[CHANNELS]":
                mode = "channels"
                continue
            elif s == "[UNITS]":
                mode = "units"
                continue
            elif s == "[DATA]":
                data_start_line = line_idx + 1
                break
            elif s.startswith("["):
                mode = None
                continue

            if mode == "channels":
                raw_parts = [p.strip() for p in s.split(":") if p.strip()]
                if not raw_parts:
                    continue

                if len(raw_parts) == 1:
                    c_name = raw_parts[0]
                else:
                    c_name = raw_parts[1]
                    if get_axis(raw_parts[-1]) is not None:
                        c_name = raw_parts[-1]
                    elif get_axis(raw_parts[1]) is not None:
                        c_name = raw_parts[1]

                channel_names.append(c_name)
            elif mode == "units":
                units.append(s)

    empty_return = (np.array([]), np.empty((0, len(channel_names))), channel_names, units, increment, [])
    if data_start_line == 0:
        return empty_return

    file_size_bytes = os.path.getsize(path)
    file_size_gb = file_size_bytes / (1024 ** 3)

    # =========================================================================
    # A) NAGY FÁJL KEZELÉSE (> 4 GB) -> HDF5 BINÁRIS UTÓLAGOS BETÖLTÉS
    # =========================================================================
    if file_size_gb > size_limit_gb:
        h5_path = os.path.basename(path) + ".h5"

        if not os.path.exists(h5_path):
            convert_tsf_to_h5(
                tsf_path=path,
                h5_path=h5_path,
                channel_names=channel_names,
                units=units,
                increment=increment,
                data_start_line=data_start_line,
                handle_gaps=handle_gaps,
                replace_9999=True,
            )

        try:
            with animated_loading(f"Reading '{f_name}.h5'"):
                is_h5 = True
                h5f = h5py.File(h5_path, "r")
                _OPEN_H5_FILES[h5_path] = h5f

                timestamps = h5f["timestamps"][:]
                data_matrix = h5f["data_matrix"][:]

                inc_val = h5f.attrs.get("increment", np.nan)
                increment_ret = float(inc_val) if not np.isnan(inc_val) else None

                gaps_ret = list(h5f["gaps"][:]) if "gaps" in h5f else []

        except Exception as e:
            print(f"ERROR while reading HDF5 file: {e}")
            return empty_return

        return timestamps, data_matrix, channel_names, units, increment_ret, gaps_ret

    # =========================================================================
    # B) KIS/KÖZEPES FÁJL KEZELÉSE (<= 4 GB)
    # =========================================================================
    try:
        with animated_loading(f"Reading '{f_name}'"):
            df = pd.read_csv(
                path, skiprows=data_start_line, sep=r"\s+", header=None, comment="[", on_bad_lines="skip", engine="c"
            )
    except Exception as e:
        print(f"ERROR while reading file: {e}")
        df = pd.DataFrame()
        input("\n\nPress ENTER to exit...")
        sys.exit(1)

    if df.empty:
        return empty_return

    ch_count = len(channel_names)
    total_cols = df.shape[1]
    time_cols = total_cols - ch_count
    if time_cols < 6:
        return empty_return

    date_cols = {k: df[i].astype(int) for i, k in enumerate(["year", "month", "day", "hour", "minute", "second"])}
    dt_series = pd.to_datetime(date_cols)
    if time_cols >= 7:
        dt_series += pd.to_timedelta(df[6] * 1000, unit="us")

    timestamps = (dt_series.astype("datetime64[ns]").astype("int64") / 1e9).to_numpy()

    try:
        data_matrix = df.iloc[:, time_cols:].to_numpy(dtype=float)
    except ValueError:
        data_matrix = df.iloc[:, time_cols:].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)

    if data_matrix.ndim == 1:
        data_matrix = data_matrix.reshape(-1, 1)
    data_matrix.setflags(write=True)

    if replace_9999:
        data_matrix[np.isclose(data_matrix, 9999.9, atol=0.1) | (data_matrix >= 9990)] = np.nan

    gaps = []
    if handle_gaps and increment is not None and len(timestamps) > 1:
        limit = increment * 1.5
        gap_indices = np.where(np.diff(timestamps) > limit)[0]
        if len(gap_indices) > 0:
            insert_indices, insert_times, insert_rows = [], [], []
            nan_row = np.full(data_matrix.shape[1], np.nan)
            for idx in gap_indices:
                t1, t2 = timestamps[idx], timestamps[idx + 1]
                gaps.append((t1, t2))
                insert_indices.extend([idx + 1, idx + 1])
                insert_times.extend([t1 + increment, t2 - increment])
                insert_rows.extend([nan_row, nan_row])
            timestamps = np.insert(timestamps, insert_indices, insert_times)
            data_matrix = np.insert(data_matrix, insert_indices, insert_rows, axis=0)

    return timestamps, data_matrix, channel_names, units, increment, gaps

# =====================================================
# Fájlok betöltése futtatáskor
# =====================================================
timestamps, data, channel_names, units, increment, gaps = load_tsf(
    filepath, handle_gaps=True, replace_9999=False
)

if len(units) < len(channel_names):
    units.extend([""] * (len(channel_names) - len(units)))

timestamps2, data2, channel_names2, units2 = None, None, [], []
if len(sys.argv) >= 3:
    try:
        timestamps2, data2, channel_names2, units2, _, _ = load_tsf(
            filepath2, handle_gaps=False, replace_9999=True
        )
    except Exception as e:
        print(f"ERROR while loading second file: {e}")

print(f"\nSamples: {len(data)}")
print(f"Channels: {len(channel_names)}\n")

# =====================================================
# Dátum tengely
# =====================================================
class DateAxis(pg.AxisItem):
    def __init__(self, orientation, position, date_only=False):
        super().__init__(orientation, position=position)
        self.date_only = date_only

    def tickStrings(self, values, scale, spacing):
        if self.date_only:
            return [
                datetime.fromtimestamp(v).strftime("%Y-%m-%d")
                for v in values
            ]

        if spacing < 1:
            return [
                datetime.fromtimestamp(v).strftime(
                    "%H:%M:%S.%f"
                )[:-3]
                for v in values
            ]

        fmt = "%H:%M:%S" if spacing < 60 else "%H:%M"

        return [
            datetime.fromtimestamp(v).strftime(fmt)
            for v in values
        ]

# =====================================================
# GUI
# =====================================================
class Viewer(QWidget):
    # ------------------------------------------------------------------
    # Inicializálás
    # ------------------------------------------------------------------
    def __init__(self, station_name, sensor_name):
        super().__init__()

        # --- 1. ALAPVETŐ VÁLTOZÓK ÉS ADATOK EGYSÉGESÍTÉSE ---
        self.station = (station_name or "").upper()
        self.sensor = (sensor_name or "").upper()

        # Közös hivatkozások az adatokra
        self.t_array = timestamps
        self.d_array = data
        self.ch_names = channel_names
        self.ch_units = units

        self.e_key_pressed = False
        self.method_state = 0
        self.show_gap_borders = False

        # --- 2. FELÜLET (UI) ÉS GRAFIKON FELÉPÍTÉSE ---
        self._setup_ui()
        self._setup_plot()

        # --- 3. ESEMÉNYEK (EVENTS) LETÖLTÉSE ÉS FELDOLGOZÁSA ---
        events_dict = self._fetch_and_parse_events()

        # Keresünk egy 8-jegyű dátumot
        date_match = re.search(r"\d{8}", base_name)

        if date_match:
            # Megnézzük a dátum utáni részt a fájlnévben
            after_date = base_name[date_match.end():]

            # Ha a 8-jegyű dátumot közvetlenül kötőjel követi (pl. 20260723-0724 vagy 20240202-20250813)
            if after_date.startswith("-"):
                self._process_multi_year_events(events_dict)
            else:
                # Sima, 1 napos dátum (pl. valami_20260723.tsf)
                self._process_single_day_events(events_dict, base_name)
        else:
            # Ha egyáltalán nincs dátum a fájlnévben
            self._process_multi_year_events(events_dict)

        # Döntés: ha BÁRMELYIK típusú esemény létezik, a gomb aktív lesz!
        has_single_day = getattr(self, 'show_event_label', False)
        has_multi_year = bool(getattr(self, 'loaded_events', []))
        self.btn_events.setEnabled(has_single_day or has_multi_year)

        # --- 4. GRAFIKON ADATAINAK ÉS HÉZAGJAINAK (GAPS) KIRAJZOLÁSA ---
        self._draw_initial_data()
        self._setup_gaps()

        # --- 5. BEFEJEZŐ INICIALIZÁLÁS ---
        self.update_event_markers()
        self.current = 0
        self.change_channel(0)

    def _setup_ui(self):
        """Létrehozza az ablakot, a legördülő menüt, a gyorsgombokat és a gombsort."""
        if is_h5:
            self.setWindowTitle(f"TSF Viewer - {filename}.h5")
        else:
            self.setWindowTitle(f"TSF Viewer - {filename}")
        self.main_layout = QVBoxLayout(self)

        # Csatornaválasztó (ComboBox)
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.change_channel)
        for c in self.ch_names:
            self.combo.addItem(c)
        self.main_layout.addWidget(self.combo)

        self.installEventFilter(self)

        # Gyorsbillentyűk
        QShortcut(QKeySequence("r"), self).activated.connect(self.reset)
        QShortcut(QKeySequence("g"), self).activated.connect(self.toggle_gap_borders)
        QShortcut(QKeySequence("i"), self).activated.connect(self.toggle_event_label)
        QShortcut(QKeySequence("m"), self).activated.connect(self.toggle_method)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.esc_clear)

        # === GOMBSOR LÉTREHOZÁSA ===
        btn_layout = QHBoxLayout()

        def _create_btn(text, callback, enabled=True):
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            if callback: btn.clicked.connect(callback)
            btn.setEnabled(enabled)
            btn_layout.addWidget(btn)
            return btn

        self.btn_reset = _create_btn("[R] Reset view", self.reset)
        self.btn_gaps = _create_btn("[G] Show/hide gap boarders", self.toggle_gap_borders)
        self.btn_events = _create_btn("[I] Show/hide event(s)", self.toggle_event_label)
        self.btn_method = _create_btn("[M] Toggle Method", self.toggle_method, enabled=False)
        self.btn_ch = _create_btn("[A-Z] Quick channel select", None, enabled=False)
        self.btn_index = _create_btn("[Left click] Get index", None, enabled=False)
        self.btn_eq = _create_btn("[E + Left click] Get earthquake", None, enabled=False)

        # Állapotjelző címke
        self.lbl_method = QLabel("")
        self.lbl_method.setStyleSheet(
            "font-weight: bold; color: #00FF00; background-color: #222; padding: 4px 8px; border-radius: 4px;")

        btn_layout.addStretch()
        btn_layout.addWidget(self.lbl_method)
        self.main_layout.addLayout(btn_layout)

    def _setup_plot(self):
        """Grafikon (PlotWidget) inicializálása és eseménykezelők bekötése."""
        axis_top = DateAxis("top", "top", date_only=True)
        axis_bottom = DateAxis("bottom", "bottom", date_only=False)

        self.plot = pg.PlotWidget(axisItems={"bottom": axis_bottom, "top": axis_top})
        self.main_layout.addWidget(self.plot)
        self.plot.installEventFilter(self)
        self.plot.scene().sigMouseClicked.connect(self.on_plot_clicked)

    def _setup_gaps(self):
        """Hézagokat jelző régiók (LinearRegionItem) inicializálása."""
        self.gap_regions = []
        transparent_pen = pg.mkPen(color=(0, 0, 0, 0))

        for start, end in gaps:
            region = pg.LinearRegionItem(
                values=(start, end), movable=False, brush=(255, 0, 0, 40),
                pen=transparent_pen, hoverPen=transparent_pen
            )
            region.setZValue(-100)
            self.plot.addItem(region)
            self.gap_regions.append(region)

        if not self.gap_regions:
            self.btn_gaps.setEnabled(False)

    def _draw_initial_data(self):
        """Fő görbék és rétegek grafikonhoz adása."""
        self.curve = self.plot.plot(self.t_array, self.d_array[:, 0], pen=pg.mkPen("r", width=line_width))
        self.curve.setDownsampling(auto=True)
        self.curve.setClipToView(True)

        self.scatter2 = self.plot.plot([], [], pen=None, symbol='o', symbolBrush=occurrence_marker_color, symbolPen=occurrence_marker_color, symbolSize=occurrence_marker_size)
        self.plot.showGrid(x=True, y=True)

    # ------------------------------------------------------------------
    # Adatbetöltés és feldolgozás
    # ------------------------------------------------------------------
    def _process_single_day_events(self, events, base_name):
        """Kiválogatja az 1 napos nézethez tartozó eseményeket a fájlnév alapján."""

        # Szigorú illeszkedés: csak független 8 számjegy (körülötte nincs más számjegy vagy kötőjel)
        match = re.search(r"(?<![\d-])\d{8}(?![\d-])", base_name)
        if not match:
            print("No single date in filename")
            return

        try:
            file_date = datetime.strptime(match.group(0), "%Y%m%d")
        except ValueError:
            return

        file_date_str = file_date.strftime("%Y.%m.%d.")
        print("File date:", file_date_str)

        file_ts = file_date.replace(hour=12).timestamp()
        matched_event_texts = []

        for date_str, event_text in events.items():
            try:
                start_part, _, end_part = date_str.strip().partition("-")
                start_part = start_part.strip().rstrip(".")

                dt_start = datetime.strptime(start_part, "%Y.%m.%d").replace(hour=0, minute=0, second=0)

                if end_part:
                    end_part = end_part.strip().rstrip(".")
                    end_date_str = f"{start_part.rsplit('.', 1)[0]}.{end_part.zfill(2)}" if len(
                        end_part) <= 2 else end_part
                    dt_end = datetime.strptime(end_date_str, "%Y.%m.%d").replace(hour=23, minute=59, second=59)
                else:
                    dt_end = dt_start.replace(hour=23, minute=59, second=59)

                if dt_start.timestamp() <= file_ts <= dt_end.timestamp():
                    matched_event_texts.append(event_text)
            except Exception:
                if date_str.strip().rstrip(".") == file_date_str.rstrip("."):
                    matched_event_texts.append(event_text)

        if not matched_event_texts:
            print("No events found for this date")
            return

        print("Matching events found for this date")
        formatted_text = '<hr style="border: 0; border-top: 1px solid #00FFCC; margin: 6px 0;">'.join(
            matched_event_texts)

        font_size = getattr(self, 'font_size', 10)

        html_text = f"""
        <div style="color: #00FFCC; font-family: monospace; font-size: {font_size}pt;">
            <b style="font-size: {font_size + 1}pt;">[ EVENT INFO ]</b><br>
            <b>Date: {file_date_str}</b>
            <hr style="border: 0; border-top: 1px solid #00FFCC; margin: 6px 0;">
            <div style="line-height: 1.3;">{formatted_text}</div>
        </div>
        """

        # Pop-up létrehozása
        parent_widget = self.plot.scene().views()[0] if self.plot.scene().views() else self.plot
        self.event_label = QTextBrowser(parent_widget)
        self.event_label.setStyleSheet("""
            QTextBrowser { background-color: rgba(15, 15, 15, 235); color: #00FFCC; border: 1px solid #00FFCC; border-radius: 4px; padding: 4px; }
            QScrollBar:vertical { background: rgba(30, 30, 30, 200); width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #00FFCC; min-height: 20px; border-radius: 3px; }
        """)

        self.event_label.setHtml(html_text)
        self.event_label.document().setTextWidth(425)
        calc_height = min(max(int(self.event_label.document().size().height()) + 20, 70), 300)

        self.event_label.resize(450, calc_height)
        self.event_label.move(60, 55)
        self.show_event_label = True

    def _process_multi_year_events(self, events):
        """Kigyűjti a grafikonra pozicionálandó (többéves) eseményjelölőket."""
        print("Multi day file detected")
        self.loaded_events = []
        if len(self.t_array) == 0: return

        valid_t = self.t_array[~np.isnan(self.t_array)]
        t_min, t_max = (valid_t[0], valid_t[-1]) if len(valid_t) > 0 else (0, float('inf'))

        for date_str, event_text in events.items():
            try:
                start_part, _, end_part = date_str.strip().partition("-")
                start_part = start_part.strip().rstrip(".")

                if end_part:
                    end_part = end_part.strip().rstrip(".")
                    end_date_str = f"{start_part.rsplit('.', 1)[0]}.{end_part.zfill(2)}" if len(
                        end_part) <= 2 else end_part
                    display_date_str = f"{start_part}. - {end_date_str}."
                else:
                    display_date_str = f"{start_part}."

                ts = datetime.strptime(start_part, "%Y.%m.%d").replace(hour=12).timestamp()

                if t_min <= ts <= t_max:
                    diffs = np.abs(self.t_array - ts)
                    idx = 0 if np.isnan(diffs).all() else np.nanargmin(diffs)

                    self.loaded_events.append({
                        'idx': idx, 'timestamp': ts, 'date_str': display_date_str, 'text': event_text
                    })
            except Exception as e:
                print(f"ERROR while processing date ({date_str}): {e}")

        if self.loaded_events:
            print(f"Events mapped to plot: {len(self.loaded_events)}\n")

    def _fetch_and_parse_events(self):
        """Letölti a szerverről a logokat, és kinyeri az egyező eseményeket egy szótárba."""
        run_id = uuid.uuid4().hex[:8]
        datumok_csv = f"datumok_{run_id}.csv"
        log_txt = f"log_for_{self.sensor.lower()}_{run_id}.txt"
        temp_csv = f"temp_{run_id}.csv"
        events = {}

        # Minta optimalizálása (RegEx)
        def _get_pattern(val):
            if not val: return None
            match = re.search(r"([A-Z]+)(\d+)$", val)
            if match:
                prefix, num = match.groups()
                return re.compile(rf"{prefix}0*{num}")
            return re.compile(re.escape(val))

        sensor_pattern = _get_pattern(self.sensor)
        station_pattern = _get_pattern(self.station)

        def _parse_csv_to_events(csv_path, check_pattern=False):
            if not os.path.exists(csv_path): return
            try:
                with open(csv_path, "r", encoding="utf-8", newline="") as fin:
                    reader = csv.reader(fin, delimiter=";")
                    for row in reader:
                        if len(row) < 2: continue

                        date, new_text = row[0], row[1]

                        if check_pattern:
                            text_upper = new_text.upper()
                            if not ((station_pattern and station_pattern.search(text_upper)) or
                                    (sensor_pattern and sensor_pattern.search(text_upper))):
                                continue

                        if date in events:
                            events[
                                date] += f'<hr style="border: 0; border-top: 1px solid #00FFCC; margin: 6px 0;">{new_text}'
                        else:
                            events[date] = new_text
            except Exception as e:
                print(f"ERROR while reading file {csv_path}: {e}")

        try:
            # Fájlok generálása
            try:
                ftp_service.convert_to_csv(datumok_txt, datumok_csv)
            except Exception:
                pass

            try:
                ftp_service.download_log(self.sensor, log_txt)
                ftp_service.convert_to_csv(log_txt, temp_csv)
            except Exception:
                pass

            # Fájlok beolvasása
            _parse_csv_to_events(datumok_csv, check_pattern=True)
            _parse_csv_to_events(temp_csv, check_pattern=False)

        finally:
            # Biztonságos takarítás (nincs több locals() ellenőrzés)
            for path in (datumok_csv, log_txt, temp_csv):
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

        print("Total events in log:", len(events))
        return events

    # ------------------------------------------------------------------
    # GUI frissítés
    # ------------------------------------------------------------------
    def position_event_popup(self, x_val, y_val):
        """Kiszámolja az eseményjelölő pontos pixelpozícióját és alá középre igazítja a dobozt."""
        popup = getattr(self, 'event_popup', None)

        # 1. Korai kilépés, ha nincs popup vagy nem látható
        if popup is None or not popup.isVisible():
            return

        # 2. Adatkoordináta átalakítása képernyő (widget) pixelkoordinátává
        vb = self.plot.plotItem.vb
        view_point = vb.mapFromView(Point(x_val, y_val))
        scene_point = vb.mapToScene(view_point)
        widget_point = self.plot.mapFromScene(scene_point)

        # 3. Popup méretek és a tervezett pozíció kiszámítása
        box_w, box_h = popup.width(), popup.height()

        x_pixel = int(widget_point.x() - box_w / 2)  # X: vízszintesen középre
        y_pixel = int(widget_point.y() + 25)  # Y: 25 pixellel az ikon alá

        # 4. Biztonsági korlátozás (clamping): ne lógjon le a plotról (10 px margó)
        plot_w, plot_h = self.plot.width(), self.plot.height()

        x_pixel = max(10, min(x_pixel, plot_w - box_w - 10))
        y_pixel = max(10, min(y_pixel, plot_h - box_h - 10))

        popup.move(x_pixel, y_pixel)

    def update_event_markers(self):
        """
        Inicializálja és frissíti az eseményjelölőket és a
        függőleges segédvonalakat, beállítja az interaktív kurzoreseményeket,
        valamint szabályozza azok láthatóságát és pozícióját a nézet állapota alapján.
        """
        events = getattr(self, 'loaded_events', None)

        # 1. Ha nincsenek betöltött események, elrejtjük a meglévő elemeket és kilépünk
        if not events:
            if getattr(self, 'event_markers', None):
                self.event_markers.setVisible(False)
            if getattr(self, 'event_lines', None):
                self.event_lines.setVisible(False)
            return

        # 2. Alapértelmezett állapot és nézet-frissítő esemény bekötése (csak egyszer)
        if not hasattr(self, 'event_toggle_state'):
            self.event_toggle_state = 0

        if not getattr(self, '_range_connected', False):
            self.plot.getViewBox().sigRangeChanged.connect(self.update_event_markers_position)
            self._range_connected = True

        vb = self.plot.getViewBox()

        # 3. Függőleges vonalak konténerének inicializálása
        if getattr(self, 'event_lines', None) is None:
            self.event_lines = pg.PlotCurveItem(
                pen=pg.mkPen(color='#00FFCC', width=1.0)
            )
            vb.addItem(self.event_lines, ignoreBounds=True)

        # 4. Eseményjelölő ikonok (ScatterPlotItem) és kurzoresemények inicializálása
        if getattr(self, 'event_markers', None) is None:
            custom_pin = pg.QtGui.QPainterPath()
            custom_pin.moveTo(-0.5, -0.5)
            custom_pin.lineTo(0.5, -0.5)
            custom_pin.lineTo(0, 0.5)
            custom_pin.closeSubpath()

            pointing_hand = getattr(Qt.CursorShape, 'PointingHandCursor', getattr(Qt, 'PointingHandCursor', None))
            arrow_hand = getattr(Qt.CursorShape, 'ArrowCursor', getattr(Qt, 'ArrowCursor', None))

            self.event_markers = pg.ScatterPlotItem(
                size=event_marker_size,
                pen=pg.mkPen(color='#00FFCC', width=1.5),
                brush=pg.mkBrush(0, 255, 204, 150),
                symbol=custom_pin,
                hoverable=True
            )

            def _on_marker_hover(ev):
                if ev.isEnter():
                    self.plot.setCursor(pointing_hand)
                elif ev.isExit():
                    self.plot.setCursor(arrow_hand)

            self.event_markers.hoverEvent = _on_marker_hover
            vb.addItem(self.event_markers, ignoreBounds=True)

        # 5. Pozíciók és láthatóság frissítése az aktuális beállítások alapján
        self.update_event_markers_position()

        self.event_markers.setVisible(self.event_toggle_state in (0, 1))
        self.event_lines.setVisible(self.event_toggle_state == 1)

        # 6. Aktív popup pozíciójának frissítése (ha nyitva van)
        popup = getattr(self, 'event_popup', None)
        active_ts = getattr(self, 'active_event_ts', None)

        if popup and popup.isVisible() and active_ts is not None:
            y_max = self.plot.plotItem.vb.viewRange()[1][1]
            self.position_event_popup(active_ts, y_max)

    def update_event_markers_position(self):
        """
        Az eseményjelölő ikonokat mindig a látható Y-tartomány legtetejére pozicionálja,
        frissíti a hozzájuk tartozó függőleges segédvonalakat,
        valamint igazítja az aktív infóablak pozícióját.
        """
        markers = getattr(self, 'event_markers', None)
        events = getattr(self, 'loaded_events', None)

        if not markers or not events:
            return

        vb = self.plot.plotItem.vb

        # 1. Jelenleg látható Y-tartomány lekérése
        y_min, y_max = vb.viewRange()[1]

        # 2. Biztonságos Y pozíció kiszámítása (ne pont a határvonalon legyen)
        # Kb. 2%-kal lejjebb hozzuk a tetejétől, hogy a PyQtGraph sose vágja le (clipping)
        y_margin = (y_max - y_min) * 0.004
        safe_y_max = y_max - y_margin

        # 3. Szűrés az aktív eseményre
        active_ts = getattr(self, 'active_event_ts', None)
        if active_ts is not None:
            events_to_show = [ev for ev in events if ev['timestamp'] == active_ts]
        else:
            events_to_show = events

        # Ha valamiért üres lenne a lista, töröljük a rajzot és kilépünk
        if not events_to_show:
            markers.setData(x=[], y=[])
            if getattr(self, 'event_lines', None):
                self.event_lines.setData(x=[], y=[])
            return

        x_coords = [ev['timestamp'] for ev in events_to_show]
        y_coords = [safe_y_max] * len(x_coords)

        # 4. Adatok frissítése
        # FIGYELEM: NINCS vb.blockSignals(True)! Erre nincs szükség, mert az item-eket
        # ignoreBounds=True-val adtuk hozzá, így a setData nem vált ki újabb RangeChanged eseményt.
        markers.setData(x=x_coords, y=y_coords)

        lines = getattr(self, 'event_lines', None)
        if lines:
            x_lines = [x for x in x_coords for _ in (0, 1)]
            y_lines = [y for _ in x_coords for y in (y_min, safe_y_max)]
            lines.setData(x=x_lines, y=y_lines, connect='pairs')

        popup = getattr(self, 'event_popup', None)
        if popup and popup.isVisible() and active_ts is not None:
            self.position_event_popup(active_ts, safe_y_max)

    def update_method_display(self):
        """
        Frissíti a 2. adatfájl kirjazolását, a feliratokat,
        a grafikon címét, valamint automatikusan ki- vagy bekapcsolja a 'btn_method' gombot.
        """
        # 1. Alapvető ellenőrzések és aktuális csatorna meghatározása
        current_idx = getattr(self, 'current', 0)
        ch_names = getattr(self, 'ch_names', getattr(self, 'channel_names', []))

        if current_idx >= len(ch_names):
            return

        current_ch_name = ch_names[current_idx]
        current_axis = get_axis(current_ch_name) if current_ch_name else None

        # Globális adatok lekérése
        t2 = globals().get('timestamps2', None)
        d2 = globals().get('data2', None)
        ch2_names = globals().get('channel_names2', [])

        # 2. Egyező oszlopok/metódusok megkeresése
        matching_cols = []
        if current_axis and t2 is not None and d2 is not None and ch2_names:
            matching_cols = [
                (idx, name) for idx, name in enumerate(ch2_names) if get_axis(name) == current_axis
            ]

        has_method = bool(matching_cols)

        # 3. Gomb állapotának frissítése
        btn_method = getattr(self, 'btn_method', None)
        if btn_method:
            btn_method.setEnabled(has_method)

        # 4. Adatok és feliratok előkészítése
        all_x2, all_y2 = [], []
        method_text = ""
        cols_to_plot = []  # Csak azokat az oszlopindexeket gyűjtjük ide, amiket ki kell rajzolni
        method_state = getattr(self, 'method_state', 0)

        if not has_method:
            self.method_state = 0
        elif method_state == 2:
            method_text = "OFF"
        else:
            # Állapot: 0 (Method 1) vagy 1 (Method 2)
            if len(matching_cols) > 1:
                target_method = "method1" if method_state == 0 else "method2"
                method_text = "Method 1" if method_state == 0 else "Method 2"
                # Csak azokat az oszlopokat tartjuk meg, amiknek a nevében benne van a target_method
                cols_to_plot = [
                    idx for idx, name in matching_cols
                    if target_method in name.lower().replace(" ", "")
                ]
            else:
                col_idx, ch2_name = matching_cols[0]
                cols_to_plot = [col_idx]

                # Név formázása
                ch_upper = ch2_name.upper().replace(" ", "")
                if "METHOD1" in ch_upper:
                    method_text = "1"
                elif "METHOD2" in ch_upper:
                    method_text = "2"
                else:
                    method_text = "ACTIVE"

            # (DRY) Adatok kinyerése a kiválasztott oszlopokból egyetlen helyen!
            for col_idx in cols_to_plot:
                y_vals = d2[:, col_idx]
                valid_mask = ~np.isnan(y_vals)
                all_x2.extend(t2[valid_mask])
                all_y2.extend(y_vals[valid_mask])

        # 5. Rajzolás frissítése
        scatter2 = getattr(self, 'scatter2', None)
        if scatter2:
            scatter2.setData(all_x2, all_y2)

        # 6. UI Címke (QLabel) frissítése
        lbl = getattr(self, 'lbl_method', None)
        if lbl:
            if not method_text:
                lbl.setText("")
                lbl.setStyleSheet("background-color: transparent;")
            else:
                if method_text != "OFF":
                    lbl.setText(f"{method_text}")
                else:
                    lbl.setText(f"Method: {method_text}")
                # Színválasztás egyszerűsítve: szürke ha OFF, amúgy zöld
                text_color = "#888888" if method_text == "OFF" else occurrence_marker_color
                lbl.setStyleSheet(
                    f"font-weight: bold; color: {text_color}; background-color: #222; padding: 4px 8px; border-radius: 4px;")

        # 7. Grafikon címének frissítése
        if method_text and method_text != "OFF":
            self.plot.setTitle(f"{current_ch_name}  +  [{method_text}]")
        else:
            self.plot.setTitle(current_ch_name)

    def show_earthquake_on_plot(self, pos):
        """
        Lekéri és megjeleníti a megadott kattintási pozícióhoz tartozó legközelebbi
        földrengés adatait a grafikonon (piros pötty + HTML táblázatos információs ablak).
        """
        try:
            # 1. Kattintott koordináta és legközelebbi adatminta megkeresése
            vb = self.plot.plotItem.vb
            clicked_x = vb.mapSceneToView(pos).x()

            t_array = getattr(self, 't_array', getattr(self, 'time', None))
            d_array = getattr(self, 'd_array', getattr(self, 'data', None))
            curr_channel = getattr(self, 'current', self.combo.currentIndex() if hasattr(self, 'combo') else 0)

            if t_array is None or d_array is None:
                return

            diffs = np.abs(t_array - clicked_x)
            idx = int(np.nanargmin(diffs)) if not np.isnan(diffs).all() else 0
            self.last_clicked_idx = idx

            exact_timestamp = t_array[idx]
            y_val_for_label = d_array[idx, curr_channel]

            # A timezone-aware datetime konvertálása naive UTC datetime-má:
            target_dt = datetime.fromtimestamp(exact_timestamp, timezone.utc).replace(tzinfo=None)

            # Y pozíció meghatározása (ha az y_val_for_label NaN, a nézet felső határát használjuk)
            y_max = vb.viewRange()[1][1]
            has_valid_y = not np.isnan(y_val_for_label)
            pos_y = y_val_for_label if has_valid_y else y_max

            # 2. Előző jelölők eltávolítása
            self.clear_markers()

            # 3. GFZ lekérdezés indítása és feldolgozása
            quakes = self.get_earthquake(target_date=target_dt)
            valid_quakes = [q for q in quakes if q.get("magnitude") is not None]

            if valid_quakes:
                import textwrap

                # Időben legközelebbi rengés kiválasztása
                closest_quake = min(valid_quakes, key=lambda q: abs(q["datetime"] - target_dt))

                event_id = closest_quake.get('event_id', 'N/A')
                mag = closest_quake.get('magnitude_raw', 'N/A')
                mag_type = closest_quake.get('mag_type', '')
                lat = closest_quake.get('latitude', 'N/A')
                lon = closest_quake.get('longitude', 'N/A')
                depth = closest_quake.get('depth', 'N/A')
                place = closest_quake.get('place', 'N/A')

                clicked_dt_str = target_dt.strftime('%Y.%m.%d. %H:%M:%S')
                q_time = closest_quake['datetime'].strftime('%Y.%m.%d. %H:%M:%S')
                wrapped_place = "<br>".join(textwrap.wrap(place, width=28))

                html_text = f"""
                <div style="color: #FF6666; font-family: monospace; font-size: {font_size}pt; padding: 6px;">
                    <b>[ EARTHQUAKE INFO ]</b><br>
                    <table style="color: #FF6666; font-family: monospace; font-size: {font_size}pt; border-collapse: collapse;">
                        <tr>
                            <td style="vertical-align: top; padding-right: 10px;"><b>Event ID:</b></td>
                            <td style="vertical-align: top;"><b>{event_id}</b></td>
                        </tr>
                        <tr>
                            <td style="vertical-align: top; padding-right: 10px;"><b>Target date:</b></td>
                            <td style="vertical-align: top;"><b>{clicked_dt_str}</b></td>
                        </tr>
                        <tr>
                            <td style="vertical-align: top; padding-right: 10px;"><b>Found date:</b></td>
                            <td style="vertical-align: top;"><b>{q_time}</b></td>
                        </tr>
                        <tr>
                            <td style="vertical-align: top; padding-right: 10px;"><b>Mag:</b></td>
                            <td style="vertical-align: top;"><b>{mag} {f'({mag_type})' if mag_type else ''}</b></td>
                        </tr>
                        <tr>
                            <td style="vertical-align: top; padding-right: 10px;"><b>Lat/Lon:</b></td>
                            <td style="vertical-align: top;"><b>{lat}, {lon}</b></td>
                        </tr>
                        <tr>
                            <td style="vertical-align: top; padding-right: 10px;"><b>Depth:</b></td>
                            <td style="vertical-align: top;"><b>{depth} km</b></td>
                        </tr>
                        <tr>
                            <td style="vertical-align: top; padding-right: 10px;"><b>Location:</b></td>
                            <td style="vertical-align: top;"><b>{wrapped_place}</b></td>
                        </tr>
                    </table>
                </div>
                """
            else:
                html_text = f"""
                <div style="color: #FFAA00; font-family: monospace; font-size: {font_size}pt; font-weight: bold; padding: 6px;">
                    [ EARTHQUAKE INFO ]<br>
                    Target date: {target_dt.strftime('%Y.%m.%d. %H:%M:%S')}<br>
                    Earthquake not found
                </div>
                """

            # 4. Pirosas pötty kirajzolása (csak ha van érvényes Y érték)
            if has_valid_y:
                self.click_dot = pg.ScatterPlotItem(
                    size=12,
                    pen=pg.mkPen(color='#FF6666', width=1),
                    brush=pg.mkBrush(color='#FF6666')
                )
                self.plot.addItem(self.click_dot)
                self.click_dot.setData(x=[exact_timestamp], y=[y_val_for_label])

            # 5. Információs címke elhelyezése
            self.click_label = pg.TextItem(
                anchor=(1.02, 1.02),
                border=pg.mkPen(color='#FF6666', width=1.5),
                fill=pg.mkBrush(15, 15, 15, 230)
            )
            self.plot.plotItem.addItem(self.click_label, ignoreBounds=True)
            self.click_label.setHtml(html_text)
            self.click_label.setPos(exact_timestamp, pos_y)

            self.is_earthquake_active = True

        except Exception as e:
            self.is_earthquake_active = False
            print(f"ERROR while getting data for earthquake: {str(e)}")

    def fit_view_to_data(self):
        """
        Az ábra tartalmát az ablakhoz igazítja úgy, hogy az X és Y tengelyen is
        hagy egy kis margót (puffert) a széleken, és megelőzi az autoRange bugot.
        """
        if self.t_array is None or self.d_array is None or len(self.t_array) == 0:
            return

        curr_channel = getattr(self, 'current', 0)
        channel_data = self.d_array[:, curr_channel]
        valid_mask = ~np.isnan(channel_data)

        if not np.any(valid_mask):
            return

        # --- X tengely margó számítása (2% puffer kétoldalt, hogy ne a szélétől induljon) ---
        x_min_raw, x_max_raw = self.t_array[0], self.t_array[-1]
        x_span = x_max_raw - x_min_raw
        x_margin = x_span * 0.02 if x_span != 0 else 1.0

        x_min_padded = x_min_raw - x_margin
        x_max_padded = x_max_raw + x_margin

        # --- Y tengely margó számítása (5% puffer alul-felül) ---
        valid_y = channel_data[valid_mask]
        y_min_raw, y_max_raw = np.min(valid_y), np.max(valid_y)

        y_span = y_max_raw - y_min_raw
        y_margin = y_span * 0.05 if y_span != 0 else 1.0

        y_min_padded = y_min_raw - y_margin
        y_max_padded = y_max_raw + y_margin

        view_box = self.plot.plotItem.vb

        # 1. Letiltjuk az autoRange-et a stabil megjelenítésért
        view_box.disableAutoRange()

        # 2. Beállítjuk a kiterjesztett (kicsit kizoomolt) tartományokat
        view_box.setRange(
            xRange=(x_min_padded, x_max_padded),
            yRange=(y_min_padded, y_max_padded),
            padding=0
        )

        # 3. Frissítjük a látható eseményjelölők pozícióját
        if hasattr(self, 'update_event_markers_position'):
            self.update_event_markers_position()

    def clear_markers(self):
        """Eltávolítja a grafikonról a kattintási jelölőpontot és a címkét."""
        if getattr(self, 'click_dot', None) is not None:
            self.plot.removeItem(self.click_dot)
            self.click_dot = None

        if getattr(self, 'click_label', None) is not None:
            self.plot.removeItem(self.click_label)
            self.click_label = None

    # ------------------------------------------------------------------
    # Felhasználói inputok
    # ------------------------------------------------------------------
    def change_channel(self, index):
        # 1. Korai kilépés, ha a grafikon vagy a görbe még nem létezik
        if getattr(self, 'plot', None) is None or getattr(self, 'curve', None) is None:
            return

        y = self.d_array[:, index]
        self.current = index
        self.curve.setData(self.t_array, y)

        # 2. Megjelenítés és tengelyek frissítése
        self.update_method_display()

        bottom_axis = self.plot.getAxis("bottom")
        bottom_axis.enableAutoSIPrefix(False)

        # Aktualizáljuk a mértékegységet
        current_unit = str(self.ch_units[index]) if index < len(self.ch_units) else ""
        self.plot.setLabel("left", current_unit)
        self.plot.setLabel("bottom", "time")

        # 3. Nézet frissítése ELŐBB (beállítjuk az új csatorna Y-skáláját)
        if hasattr(self, 'fit_view_to_data'):
            self.fit_view_to_data()

        if hasattr(self, 'update_event_markers'):
            self.update_event_markers()

        # 4. Aktív jelölő (Sima kattintás VAGY Földrengés) frissítése az új csatorna Y-értékére
        if getattr(self, 'last_clicked_idx', None) is not None:
            idx = int(self.last_clicked_idx)

            # Explicit típuskonverzió (Windows / PySide C++ kompatibilitás)
            exact_timestamp = float(self.t_array[idx])
            new_y = float(y[idx])
            has_valid_y = not np.isnan(new_y)

            # =========================================================================
            # A) HA FÖLDRENGÉS INFO VAN AKTÍVAN (is_earthquake_active == True)
            # =========================================================================
            if getattr(self, 'is_earthquake_active', False):
                vb = self.plot.plotItem.vb
                y_max = float(vb.viewRange()[1][1])
                pos_y = new_y if has_valid_y else y_max

                # Piros pötty áthelyezése az új csatorna Y értékére
                if getattr(self, 'click_dot', None) is not None:
                    if has_valid_y:
                        self.click_dot.setData(x=[exact_timestamp], y=[new_y])
                        self.click_dot.show()
                    else:
                        self.click_dot.hide()

                # Piros földrengés ablak áthelyezése az új Y pozícióra (szöveg marad!)
                if getattr(self, 'click_label', None) is not None:
                    self.click_label.setPos(exact_timestamp, pos_y)
                    self.click_label.update()

            # =========================================================================
            # B) HA SIMA ADATMINTA (sárga pötty + sárga label) VAN AKTÍVAN
            # =========================================================================
            else:
                # Sárga pötty áthelyezése
                if getattr(self, 'click_dot', None) is not None:
                    if has_valid_y:
                        self.click_dot.setData(x=[exact_timestamp], y=[new_y])
                        self.click_dot.show()
                    else:
                        self.click_dot.hide()

                # Címke HTML szövegének ÉS pozíciójának frissítése az új adatra + mértékegységre
                if getattr(self, 'click_label', None) is not None:
                    # A tengely lekérdezése HELYETT közvetlenül az új csatorna mértékegységét használjuk!
                    unit_display = current_unit if current_unit else "Value"

                    # Biztonságos időbélyeg formázás
                    try:
                        dt = datetime.fromtimestamp(exact_timestamp, tz=timezone.utc)
                        date_str = dt.strftime('%Y.%m.%d.')
                        tmstmp_str = dt.strftime('%H:%M:%S.%f')[:-3]
                    except Exception:
                        date_str = "N/A"
                        tmstmp_str = f"{exact_timestamp:.3f}"

                    html_text = f"""
                    <div style="color: #FFFF00; font-family: monospace; font-size: {font_size}pt; font-weight: bold; padding: 5px;">
                        Index: {idx}<br>
                        Date: {date_str}<br>
                        Timestamp: {tmstmp_str}<br>
                        {unit_display}: {new_y:.4f}
                    </div>
                    """

                    self.click_label.setHtml(html_text)
                    self.click_label.setPos(exact_timestamp, new_y)
                    self.click_label.update()

        # Kényszerített grafikon újrarajzolás Windows alatt
        self.plot.update()

    def toggle_gap_borders(self):
        """
        Ki- és bekapcsolja a gap-eket jelölő tartományok szélein lévő
        határvonalak láthatóságát.
        """
        # 1. Állapot megfordítása (True <-> False)
        self.show_gap_borders = not getattr(self, 'show_gap_borders', False)

        # 2. Megfelelő toll (pen) kiválasztása a jelenlegi állapot alapján
        new_pen = (
            pg.mkPen((255, 255, 0, 190), width=1)
            if self.show_gap_borders
            else pg.mkPen(color=(0, 0, 0, 0))
        )

        # 3. Határvonalak frissítése az összes adathiány régióban
        for region in getattr(self, 'gap_regions', []):
            for line in region.lines:
                line.setPen(new_pen)
                line.setHoverPen(new_pen)

    def toggle_event_label(self):
        """
        Ciklikusan lépteti vagy ki/be kapcsolja az események kijelzését a fájl típusa alapján.
        - Többéves fájlnál (3 állapot): 0 -> Csak jelölők | 1 -> Jelölők + Vonalak | 2 -> Minden rejtve (beleértve a popupot is)
        - Egynapos fájlnál (2 állapot): Vált az infóablak láthatósága között (Látható <-> Rejtve)
        """
        is_multi_year = bool(getattr(self, 'loaded_events', None))

        # Grafikus elemek hivatkozásainak lekérése
        markers = getattr(self, 'event_markers', None)
        lines = getattr(self, 'event_lines', None)

        # Biztosítjuk a kompatibilitást mindkét elnevezéssel (event_popup / event_label)
        popup = getattr(self, 'event_popup', getattr(self, 'event_label', None))

        if is_multi_year:
            # === TÖBBÉVES FÁJL: 3-lépcsős ciklikus váltás (0 -> 1 -> 2 -> 0) ===
            current_state = getattr(self, 'event_toggle_state', 0)
            self.event_toggle_state = (current_state + 1) % 3

            show_markers = self.event_toggle_state in (0, 1)
            show_lines = self.event_toggle_state == 1
        else:
            # === EGYNAPOS FÁJL: Egyszerű 2-lépcsős (ki/be) kapcsolás ===
            self.show_event_label = not getattr(self, 'show_event_label', True)

            show_markers = False
            show_lines = False

        # --- LÁTHATÓSÁGOK BEÁLLÍTÁSA ---
        if markers:
            markers.setVisible(show_markers)
        if lines:
            lines.setVisible(show_lines)

        # Popup / Label láthatóságának vezérlése
        if popup:
            if is_multi_year:
                # Többéves fájlnál a toggle állapota és az aktív esemény dönt
                if not show_markers and not show_lines:
                    popup.hide()
                elif getattr(self, 'active_event_ts', None) is not None:
                    popup.show()
            else:
                # Egynapos fájlnál kizárólag a show_event_label változó dönt
                if getattr(self, 'show_event_label', True):
                    popup.show()
                else:
                    popup.hide()

    def toggle_method(self):
        current_idx = getattr(self, 'current', 0)
        ch_names = self.channel_names if hasattr(self, 'channel_names') else channel_names

        current_ch_name = ch_names[current_idx] if current_idx < len(ch_names) else ""
        current_axis = get_axis(current_ch_name)

        # Megszámoljuk, hány metódus tartozik a jelenlegi tengelyhez a 2. fájlban
        matching_count = 0
        if 'channel_names2' in globals() and current_axis:
            matching_count = sum(1 for ch2 in channel_names2 if get_axis(ch2) == current_axis)

        if not hasattr(self, 'method_state'):
            self.method_state = 0

        if matching_count > 1:
            # 1 PLOTON TÖBB METÓDUS -> 3 állapot (Method 1 -> Method 2 -> Ki)
            self.method_state = (self.method_state + 1) % 3
        else:
            # KÜLÖN PLOTOK -> 2 állapot (Be [0] <-> Ki [2])
            self.method_state = 2 if self.method_state == 0 else 0

        self.update_method_display()

    def esc_clear(self):
        """
        Elrejti az összes aktív popup-ot a grafikonról esc billentyű lenyomására
        """
        # Index lekérdezés elrejtése
        if hasattr(self, 'click_dot') and self.click_dot is not None:
            try:
                self.plot.removeItem(self.click_dot)
            except Exception:
                pass
            self.click_dot = None

        if hasattr(self, 'click_label') and self.click_label is not None:
            try:
                self.plot.plotItem.removeItem(self.click_label)
            except Exception:
                pass
            self.click_label = None

        if hasattr(self, 'clear_markers') and callable(self.clear_markers):
            self.clear_markers()

        # Event info elrejtése
        popup = getattr(self, 'event_popup', None)
        if popup is not None:
            popup.hide()

        # Earthquake info elrejtése
        self.e_key_pressed = False  # E-gomb mód kikapcsolása
        if hasattr(self, 'clear_earthquake') and callable(self.clear_earthquake):
            self.clear_earthquake()  # Ha van külön földrengés törlő metódusod
        elif hasattr(self, 'eq_item') and self.eq_item is not None:
            try:
                self.plot.removeItem(self.eq_item)
            except Exception:
                pass
            self.eq_item = None

        # Kijelölési állapotok (index, aktív esemény) alaphelyzetbe állítása
        self.last_clicked_idx = None
        self.active_event_ts = None

        # Event markers pozícióinak frissítése
        if hasattr(self, 'update_event_markers_position') and callable(self.update_event_markers_position):
            self.update_event_markers_position()

    def reset(self):
        self.fit_view_to_data()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def on_plot_clicked(self, event):
        """
        Kezeli a grafikonra való kattintásokat:
        - Bal kattintás + 'E' billentyű: földrengés adatok megjelenítése a kattintott pontban.
        - Felső sávba kattintás (eseményjelölők): esemény infóablak (popup) megnyitása/bezárása.
        - Görbére kattintás: a legközelebbi adatminta kijelölése (sárga pötty + adat címke).
        - Ismételt kattintás ugyanarra a pontra: kijelölés megszüntetése (toggle ki).
        """
        left_button = getattr(Qt.MouseButton, 'LeftButton', getattr(Qt, 'LeftButton', None))

        # 1. Csak a bal egérgombra és a grafikon területén belüli kattintásokra reagálunk
        if event.button() != left_button:
            return

        pos = event.scenePos()
        plot_rect = self.plot.plotItem.sceneBoundingRect()
        if not plot_rect.contains(pos):
            return

        # 2. Földrengés gomb mód kezelése ('E' billentyű)
        if getattr(self, 'e_key_pressed', False):
            self.show_earthquake_on_plot(pos)
            return

        try:
            vb = self.plot.plotItem.vb
            mouse_point = vb.mapSceneToView(pos)
            clicked_x, clicked_y = mouse_point.x(), mouse_point.y()

            t_array = getattr(self, 't_array', getattr(self, 'time', None))
            d_array = getattr(self, 'd_array', getattr(self, 'data', None))
            curr_channel = getattr(self, 'current', self.combo.currentIndex() if hasattr(self, 'combo') else 0)

            if t_array is None or d_array is None:
                return

            # Nézet határainak lekérése
            x_range, y_range = vb.viewRange()
            visible_width = x_range[1] - x_range[0]
            visible_height = y_range[1] - y_range[0]
            y_max = y_range[1]

            markers_visible = bool(getattr(self, 'event_markers', None) and self.event_markers.isVisible())
            is_near_top = (y_max - clicked_y) <= (0.03 * visible_height)

            # Ha a felső sávba kattintott, de a jelölők rejtve vannak -> figyelmen kívül hagyjuk
            if is_near_top and not markers_visible:
                return

            # 3. Eseményjelölőre kattintás vizsgálata
            clicked_event = None
            loaded_events = getattr(self, 'loaded_events', [])

            if is_near_top and markers_visible and loaded_events:
                threshold = 0.015 * visible_width
                active_ts = getattr(self, 'active_event_ts', None)
                events_to_check = [ev for ev in loaded_events if
                                   ev['timestamp'] == active_ts] if active_ts else loaded_events

                if events_to_check:
                    closest_ev = min(events_to_check, key=lambda ev: abs(ev['timestamp'] - clicked_x))
                    if abs(closest_ev['timestamp'] - clicked_x) <= threshold:
                        clicked_event = closest_ev

            # 4. Koordináták és index meghatározása
            if clicked_event:
                idx = clicked_event['idx']
                exact_timestamp = clicked_event['timestamp']
                y_val_for_label = y_max
                self.active_event_ts = exact_timestamp
            else:
                diffs = np.abs(t_array - clicked_x)
                idx = int(np.nanargmin(diffs)) if not np.isnan(diffs).all() else 0
                exact_timestamp = t_array[idx]
                y_val_for_label = d_array[idx, curr_channel]

                self.active_event_ts = None
                if getattr(self, 'event_popup', None):
                    self.event_popup.hide()
                self.update_event_markers_position()

            # 5. Meglévő kijelölések takarítása
            self.clear_markers()
            popup = getattr(self, 'event_popup', None)
            if popup:
                popup.hide()

            # Érvénytelen adat (NaN) vagy ugyanarra a pontra kattintás -> kijelölés törlése és kilépés
            is_nan_val = not clicked_event and np.isnan(y_val_for_label)
            is_same_point = getattr(self, 'last_clicked_idx', None) == idx

            if is_nan_val or is_same_point:
                self.last_clicked_idx = None
                self.active_event_ts = None
                if getattr(self, 'event_popup', None):
                    self.event_popup.hide()
                self.update_event_markers_position()
                return

            self.last_clicked_idx = idx

            # 6. Megjelenítés: Esemény ablak (popup) VS. Sima adatminta pont
            if clicked_event:
                raw_text = str(clicked_event.get('text', 'No data'))
                formatted_text = raw_text.replace('\n', '<br>')

                html_text = f"""
                <div style="color: #00FFCC; font-family: monospace; font-size: {font_size}pt;">
                    <b style="font-size: {font_size + 1}pt;">[ EVENT INFO ]</b><br>
                    <b>Date: {clicked_event['date_str']}</b>
                    <hr style="border: 0; border-top: 1px solid #00FFCC; margin: 6px 0;">
                    <div style="line-height: 1.3;">{formatted_text}</div>
                </div>
                """

                if getattr(self, 'event_popup', None) is None:
                    self.event_popup = QTextBrowser(self.plot)
                    self.event_popup.setStyleSheet("""
                        QTextBrowser {
                            background-color: rgba(15, 15, 15, 235);
                            color: #00FFCC;
                            border: 1px solid #00FFCC;
                            border-radius: 4px;
                            padding: 4px;
                        }
                        QScrollBar:vertical {
                            background: rgba(30, 30, 30, 200);
                            width: 10px;
                            margin: 0px;
                        }
                        QScrollBar::handle:vertical {
                            background: #00FFCC;
                            min-height: 20px;
                            border-radius: 3px;
                        }
                    """)
                    # Stílusok azonnali érvényesítése a pontos méretszámításhoz
                    self.event_popup.ensurePolished()

                self.event_popup.setHtml(html_text)

                # Dinamikus ablakméretezés kiszámítása
                popup_w, min_h, max_h = 450, 70, 300
                doc = self.event_popup.document()
                doc.setTextWidth(popup_w - 25)
                doc.adjustSize()  # Kikényszeríti a szövegelrendezés frissítését az új szélesség alapján

                calc_h = int(doc.size().height()) + 20
                actual_h = max(min_h, min(calc_h, max_h))

                self.event_popup.resize(popup_w, actual_h)
                self.position_event_popup(exact_timestamp, y_max)
                self.event_popup.show()

            else:
                # Normál adatminta kijelölése (Sárga pötty + Adat címke)
                left_axis = self.plot.getAxis('left')
                y_label = left_axis.labelText
                y_unit = left_axis.labelUnits
                unit_display = f"{y_label} [{y_unit}]" if y_unit else (y_label or "Unit")

                dt = datetime.fromtimestamp(exact_timestamp)
                date_str = dt.strftime('%Y.%m.%d.')
                tmstmp_str = dt.strftime('%H:%M:%S.%f')[:-3]

                self.click_dot = pg.ScatterPlotItem(
                    size=10,
                    pen=pg.mkPen(color='#FFFF00', width=1),
                    brush=pg.mkBrush(color='#FFFF00')
                )
                self.plot.addItem(self.click_dot)
                self.click_dot.setData(x=[exact_timestamp], y=[y_val_for_label])

                html_text = f"""
                <div style="color: #FFFF00; font-family: monospace; font-size: {font_size}pt; font-weight: bold; padding: 5px;">
                    Index: {idx}<br>
                    Date: {date_str}<br>
                    Timestamp: {tmstmp_str}<br>
                    {unit_display}: {y_val_for_label:.4f}
                </div>
                """

                self.click_label = pg.TextItem(
                    anchor=(-0.02, 1.11),
                    border=pg.mkPen(color='gray', width=1),
                    fill=pg.mkBrush(15, 15, 15, 220)
                )
                self.plot.plotItem.addItem(self.click_label, ignoreBounds=True)
                self.click_label.setHtml(html_text)
                self.click_label.setPos(exact_timestamp, y_val_for_label)

            self.update_event_markers_position()

        except Exception as e:
            print(f"ERROR: {str(e)}")

    def eventFilter(self, obj, event):
        # 1. Csak a billentyűlenyomásokat vizsgáljuk
        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(obj, event)

        # 2. Csak az érvényes betűkaraktereket kezeljük
        text = event.text()
        if not text or not text.isalpha():
            return super().eventFilter(obj, event)

        char = text.upper()
        current_idx = self.combo.currentIndex()
        total_items = self.combo.count()

        # 3. Következő illeszkedő csatorna keresése a listában
        for i in range(1, total_items + 1):
            idx = (current_idx + i) % total_items
            if self.combo.itemText(idx).upper().startswith(char):
                self.combo.setCurrentIndex(idx)
                return True  # Sikeres találat, lekezeletnek tekintjük az eseményt

        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        """
        Kezeli a billentyűlenyomásokat
        """
        key_e = getattr(getattr(Qt, 'Key', Qt), 'Key_E', None)

        if event.key() == key_e:
            self.e_key_pressed = True

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """
        Kezeli a billentyűk felengedését
        """
        key_e = getattr(getattr(Qt, 'Key', Qt), 'Key_E', None)

        if event.key() == key_e:
            self.e_key_pressed = False

        super().keyReleaseEvent(event)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def get_earthquake(self, target_date: datetime = None):
        """
        Lekéri a GEOFON FDSN webszervizéből a megadott időpontot megelőző 1 óra
        földrengési adatait 'text' (pipe-al elválasztott) formátumban.
        """
        if target_date is None:
            target_date = datetime(2023, 5, 5, 5, 3, 0)

        start_time = target_date - timedelta(hours=1)
        url = "https://geofon.gfz-potsdam.de/fdsnws/event/1/query"
        params = {
            "format": "text",
            "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": target_date.strftime("%Y-%m-%dT%H:%M:%S")
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                return []

            quakes = []
            reader = csv.reader(io.StringIO(response.text), delimiter='|')

            # Segédfüggvény az oszlopok biztonságos kiolvasásához
            def _get_field(row, idx):
                return row[idx].strip() if len(row) > idx and row[idx].strip() else "--"

            for row in reader:
                try:
                    # Érvénytelen vagy fejlécsorok kiszűrése
                    if not row or row[0].startswith("#") or len(row) < 2:
                        continue

                    time_str = _get_field(row, 1)
                    if time_str == "--":
                        continue

                    dt = datetime.fromisoformat(time_str.replace("Z", ""))
                    ts = dt.timestamp()

                    # Mezők kinyerése a szöveges formátum oszlopai alapján:
                    # 0: EventID | 1: Time | 2: Lat | 3: Lon | 4: Depth | 9: MagType | 10: Magnitude | 12: EventLocationName
                    event_id = _get_field(row, 0)
                    latitude = _get_field(row, 2)
                    longitude = _get_field(row, 3)
                    depth = _get_field(row, 4)
                    mag_type = _get_field(row, 9)
                    mag_raw = _get_field(row, 10)
                    place = _get_field(row, 12)

                    # Magnitúdó float konverziója
                    mag_val = None
                    if mag_raw != "N/A":
                        try:
                            mag_val = float(mag_raw)
                        except ValueError:
                            mag_val = None

                    quakes.append({
                        "event_id": event_id,
                        "timestamp": ts,
                        "datetime": dt,
                        "magnitude": mag_val,
                        "magnitude_raw": mag_raw,
                        "mag_type": mag_type,
                        "latitude": latitude,
                        "longitude": longitude,
                        "depth": depth,
                        "place": place,
                        "title": f"Magnitude {mag_raw} ({mag_type}) - {place}",
                        "text": f"Magnitude: {mag_raw}\nPlace: {place}"
                    })
                except Exception:
                    continue

            return quakes

        except Exception as e:
            print(f"ERROR: {str(e)}")

        return []

# =====================================================
# Start
# =====================================================
def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        # PyInstaller onefile
        base_path = sys._MEIPASS
    else:
        # normál Python
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

app = QApplication(sys.argv)
icon_path = resource_path("icon.png")
if os.path.exists(icon_path):
    app.setWindowIcon(QIcon(icon_path))
win = Viewer(station, sensor)
win.showMaximized()

sys.exit(app.exec())
