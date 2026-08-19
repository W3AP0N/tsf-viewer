import os
import sys
import time
import math
import h5py
import tomllib
import numpy as np
import pandas as pd

os.chdir(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)))

# =====================================================
# Config betöltése
# =====================================================
try:
    with open("tsf_viewer_config.toml", "rb") as config_file:
        config = tomllib.load(config_file)
except FileNotFoundError:
    config = {}

path_config = config.get("path", {})
compression_config = config.get("compression", {})
h5_save_path = compression_config.get("h5_save_path", "C:\\Users\\Public")

# =====================================================
# Segédfüggvények
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

def parse_tsf_header(path: str):
    """Fejléc információk kinyerése a TSF fájlból."""
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

    return channel_names, units, increment, data_start_line

def compute_timestamps(df_time_cols: pd.DataFrame) -> np.ndarray:
    """
    Rendkívül gyors, tiszta NumPy alapú Unix timestamp számítás.
    ~100x gyorsabb, mint a pd.to_datetime().
    """
    years = df_time_cols.iloc[:, 0].to_numpy(dtype=np.int64)
    months = df_time_cols.iloc[:, 1].to_numpy(dtype=np.int64)
    days = df_time_cols.iloc[:, 2].to_numpy(dtype=np.int64)
    hours = df_time_cols.iloc[:, 3].to_numpy(dtype=np.int64)
    minutes = df_time_cols.iloc[:, 4].to_numpy(dtype=np.int64)
    seconds = df_time_cols.iloc[:, 5].to_numpy(dtype=np.int64)

    # Hónapok előtti napok száma nem szökőévben
    days_before_month = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334], dtype=np.int64)

    y = years - 1970
    # Szökőnapok száma 1970 óta
    leap_days = (years - 1969) // 4 - (years - 1901) // 100 + (years - 1601) // 400

    # Adott év szökőév-e és február után vagyunk-e
    is_leap = ((years % 4 == 0) & (years % 100 != 0)) | (years % 400 == 0)
    leap_adj = np.where((months > 2) & is_leap, 1, 0)

    total_days = y * 365 + leap_days + days_before_month[months - 1] + (days - 1) + leap_adj
    total_secs = total_days * 86400 + hours * 3600 + minutes * 60 + seconds

    timestamps = total_secs.astype(np.float64)

    # Ha van törtmásodperc oszlop (pl. 100 ms = 0.1s)
    if df_time_cols.shape[1] >= 7:
        frac_secs = df_time_cols.iloc[:, 6].to_numpy(dtype=np.float64) / 1000.0
        timestamps += frac_secs

    return timestamps

# =====================================================
# Konvertáló főfüggvény (OPTIMALIZÁLT)
# =====================================================
def convert_tsf_to_h5(
        tsf_path: str,
        h5_path: str | None = None,
        channel_names: list[str] | None = None,
        units: list[str] | None = None,
        increment: float | None = None,
        data_start_line: int | None = None,
        handle_gaps: bool = False,
        replace_9999: bool = True,
        chunksize: int = 1_000_000,
        ask_confirmation: bool = True,
) -> str:
    global h5_save_path
    if h5_save_path == "*":
        abs_path = os.path.abspath(tsf_path)
        h5_save_path = os.path.dirname(abs_path)

    """TSF fájl átalakítása HDF5 formátumba optimális teljesítménnyel."""
    f_name = os.path.basename(tsf_path)

    if ask_confirmation:
        print(f"\n[INFO] '{f_name}' is too large")
        print("[INFO] Reading this file without compression may cause memory errors")
        choice = input("[INFO] Would you like to compress it to HDF5? [Y/n]: ").strip().lower()

        if choice not in ("y", "yes", ""):
            print("[INFO] Skipping compression")
            return None

    start_time = time.time()

    if h5_path is None:
        h5_path = os.path.join(h5_save_path, f_name + ".h5")

    if data_start_line is None or channel_names is None:
        ch, un, inc, start = parse_tsf_header(tsf_path)
        channel_names = channel_names or ch
        units = units or un
        increment = increment if increment is not None else inc
        data_start_line = data_start_line or start

    if data_start_line == 0:
        print(f"ERROR: Could not find [DATA] block in file '{tsf_path}'")
        sys.exit(1)

    tmp_h5_path = h5_path + ".tmp"
    ch_count = len(channel_names)
    all_gaps = []

    # =====================================================
    # Várható chunk szám pontos kiszámítása mintavételezéssel
    # =====================================================
    file_size_bytes = os.path.getsize(tsf_path)
    estimated_chunks = 1

    try:
        with open(tsf_path, "rb") as f_est:
            header_bytes = 0
            for _ in range(data_start_line):
                header_bytes += len(f_est.readline())

            sample_bytes = 0
            sample_lines = 0
            for _ in range(100):
                line = f_est.readline()
                if not line:
                    break
                sample_bytes += len(line)
                sample_lines += 1

            if sample_lines > 0:
                avg_bytes_per_line = sample_bytes / sample_lines
                data_bytes = max(0, file_size_bytes - header_bytes)
                estimated_lines = data_bytes / avg_bytes_per_line
                estimated_chunks = max(1, math.ceil(estimated_lines / chunksize))
    except Exception:
        estimated_chunks = 1  # Hiba esetén fallback

    # =====================================================
    # Fájl streamelése és HDF5 írás
    # =====================================================
    try:
        with h5py.File(tmp_h5_path, "w") as h5f:
            # 1. Metaadatok
            h5f.attrs["channel_names"] = channel_names
            h5f.attrs["units"] = units
            h5f.attrs["increment"] = increment if increment is not None else np.nan

            # 2. Dataset-ek inicializálása explicit chunkinggal
            dset_time = h5f.create_dataset(
                "timestamps",
                shape=(0,),
                maxshape=(None,),
                dtype="float64",
                compression="lzf",
                chunks=(100_000,),
            )
            dset_data = h5f.create_dataset(
                "data_matrix",
                shape=(0, ch_count),
                maxshape=(None, ch_count),
                dtype="float32",
                compression="lzf",
                chunks=(100_000, ch_count),
            )

            # Megnyitjuk a fájlt stream olvasásra
            with open(tsf_path, "r", encoding="utf-8", errors="ignore") as f:

                # Kézzel átugorjuk a fejlécet, így a pandas azonnal az adatokkal kezd
                for _ in range(data_start_line):
                    f.readline()

                # A nyitott fájlobjektumot adjuk át, a C engine-nel. Nulla várakozási idő!
                df_iter = pd.read_csv(
                    f,
                    sep=r"\s+",
                    header=None,
                    on_bad_lines="skip",
                    engine="c",
                    chunksize=chunksize,
                )

                # 3. Feldolgozás darabokban
                for chunk_idx, df in enumerate(df_iter):
                    sys.stdout.write(f"\r[INFO] Converting '{f_name}'... chunk {chunk_idx + 1} / ~{estimated_chunks}")
                    sys.stdout.flush()

                    if df.empty:
                        continue

                    total_cols = df.shape[1]
                    time_cols = total_cols - ch_count
                    if time_cols < 6:
                        continue

                    # 3.1. Timestamps (Szupergyors NumPy konverzió)
                    timestamps = compute_timestamps(df.iloc[:, :time_cols])

                    # 3.2. Adat mátrix
                    data_matrix = df.iloc[:, time_cols:].to_numpy(dtype=np.float32)

                    if data_matrix.ndim == 1:
                        data_matrix = data_matrix.reshape(-1, 1)

                    # 3.3. Hibás adatok cseréje
                    if replace_9999:
                        data_matrix[data_matrix >= 9990.0] = np.nan

                    # 3.4. Időbeli hézagok kezelése
                    if handle_gaps and increment is not None and len(timestamps) > 1:
                        limit = increment * 1.5
                        gap_indices = np.where(np.diff(timestamps) > limit)[0]

                        if len(gap_indices) > 0:
                            insert_indices, insert_times, insert_rows = [], [], []
                            nan_row = np.full(data_matrix.shape[1], np.nan, dtype=np.float32)

                            for idx in gap_indices:
                                t1, t2 = timestamps[idx], timestamps[idx + 1]
                                all_gaps.append((t1, t2))
                                insert_indices.extend([idx + 1, idx + 1])
                                insert_times.extend([t1 + increment, t2 - increment])
                                insert_rows.extend([nan_row, nan_row])

                            timestamps = np.insert(timestamps, insert_indices, insert_times)
                            data_matrix = np.insert(data_matrix, insert_indices, insert_rows, axis=0)

                    # 3.5. Mentés HDF5-be
                    curr_len = dset_time.shape[0]
                    new_len = curr_len + len(timestamps)

                    dset_time.resize(new_len, axis=0)
                    dset_data.resize(new_len, axis=0)

                    dset_time[curr_len:new_len] = timestamps
                    dset_data[curr_len:new_len] = data_matrix

            if all_gaps:
                h5f.create_dataset("gaps", data=np.array(all_gaps, dtype="float64"))

        # Ideiglenes fájl cseréje a véglegesre
        if os.path.exists(h5_path):
            os.remove(h5_path)
        os.rename(tmp_h5_path, h5_path)

        elapsed = time.time() - start_time
        mins, secs = divmod(elapsed, 60)
        elapsed_str = f"{int(mins)}m{secs:06.3f}s" if elapsed >= 60 else f"{elapsed:.3f}s"
        sys.stdout.write(f"\rConverting '{f_name}'... Done! ({elapsed_str}), {chunk_idx + 1} chunks -> '{h5_path}'\n")
        sys.stdout.flush()

        return h5_path

    except Exception as e:
        if os.path.exists(tmp_h5_path):
            os.remove(tmp_h5_path)
        print(f"\nERROR while converting to binary: {e}")
        sys.exit(1)

# =====================================================
# Önálló indítás
# =====================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tsf_converter.py <file.tsf>")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"ERROR: File does not exist '{input_file}'")
        sys.exit(1)

    if not input_file.lower().endswith(".tsf"):
        print(f"ERROR: '{input_file}' is not a .tsf file!")
        sys.exit(1)

    convert_tsf_to_h5(input_file, ask_confirmation=False)
    input("\nPress ENTER to exit...")
