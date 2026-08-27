import re
import os
import sys
import csv
import json
import time
import tomllib
from ftplib import FTP, all_errors

os.chdir(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)))

# =====================================================
# Alap config betöltése
# =====================================================
try:
    with open("tsf_viewer_config.toml", "rb") as config_file:
        config = tomllib.load(config_file)
except FileNotFoundError:
    config = {}

path_config = config.get("path", {})
ftp_json_path = path_config.get("ftp_json", "tsf_viewer_ftp.json")

# =====================================================
# Exception
# =====================================================
class DownloadTimeoutError(Exception):
    pass

# =====================================================
# FTP config betöltése
# =====================================================
FTP_CONFIG = {}

try:
    with open(ftp_json_path, "r", encoding="utf-8") as ftp_config_file:
        FTP_CONFIG = json.load(ftp_config_file)
except FileNotFoundError:
    pass

# --- REGEX KONSTANSOK ---
# Csak egyszer fordul le a program indításakor, hatékonyabb.
SEP = r'[-_./]'
p1 = r'(?P<y1>\d{4})' + SEP + r'(?P<m1>\d{1,2})' + SEP + r'(?P<d1>\d{1,2})'
p2 = r'(?P<d2>\d{1,2})' + SEP + r'(?P<m2>\d{1,2})' + SEP + r'(?P<y2>\d{4})'
p3 = r'(?P<d3>\d{1,2})' + SEP + r'(?P<m3>\d{1,2})' + SEP + r'(?P<y3>\d{2})'
p4 = (
    r'(?P<y4>(?:19|20)\d{2})'
    r'(?P<m4>0[1-9]|1[0-2])'
    r'(?P<d4>0[1-9]|[12]\d|3[01])'
)
DATE_REGEX = re.compile(rf'(?<!\()\b(?:{p1}|{p2}|{p3}|{p4})\b(?!\))')

def download_log(sensor, output_file):
    max_download_time = 15
    if sensor not in FTP_CONFIG:
        print(f"[WARNING] No FTP data for sensor '{sensor}'")
        return False

    sensor_info = FTP_CONFIG[sensor]
    filename = f"log_for_{sensor.lower()}.txt"
    start_time = time.time()
    file_created = False

    def _cleanup_file(file_path, file_created):
        if file_created and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    try:
        print(f"Downloading '{filename}'...", end="", flush=True)
        with FTP(sensor_info["host"], timeout=15) as ftp:
            ftp.login(user=sensor_info["user"], passwd=sensor_info["passwd"])

            if "path" in sensor_info:
                ftp.cwd(sensor_info["path"])

            with open(output_file, "wb") as local_file:
                file_created = True

                def handle_chunk(data):
                    if time.time() - start_time > max_download_time:
                        raise DownloadTimeoutError()

                    local_file.write(data)

                ftp.retrbinary(f"RETR {filename}", handle_chunk)

            # Siker esetén közvetlenül mögé írja
            print(" Done!")
            return True

    except DownloadTimeoutError:
        print(" TIMEOUT! (>15.000s)")
        print("[WARNING] Skipping download!")
        _cleanup_file(output_file, file_created)
        return False

    except all_errors as e:
        print(" FAILED!")
        print(f"[FTP ERROR] While processing: {e}")
        return False

    except IOError as e:
        print(" FAILED!")
        print(f"[ERROR] While writing local file: {e}")
        return False

def convert_to_csv(input_filepath, output_filepath):
    def _parse_and_format_date(line):
        """Megkeresi a dátumot a sorban, és YYYY.MM.DD. formátumra alakítja."""
        m = DATE_REGEX.search(line)
        if not m:
            return None, line

        d = m.groupdict()

        if d.get('y1'):
            year, month, day = d['y1'], d['m1'], d['d1']
        elif d.get('y2'):
            year, month, day = d['y2'], d['m2'], d['d2']
        elif d.get('y3'):
            year, month, day = f"20{d['y3']}", d['m3'], d['d3']
        elif d.get('y4'):
            year, month, day = d['y4'], d['m4'], d['d4']

        formatted_date = f"{year}.{month.zfill(2)}.{day.zfill(2)}."

        matched_str = m.group(0)
        clean_text = line.replace(matched_str, '').strip()
        clean_text = re.sub(r'^\.\s*', '', clean_text)

        return formatted_date, clean_text

    # --- Fájl beolvasás ---
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(input_filepath, 'r', encoding='iso-8859-1') as f:
            lines = f.readlines()
    except Exception:
        return False

    entries = []
    current_date = None
    current_text = []

    for line in lines:
        line = line.strip()

        if not line or re.match(r'^[-.]{3,}$', line):
            continue

        found_date, rest_of_line = _parse_and_format_date(line)

        if found_date:
            if current_date:
                full_text = " ".join(current_text).strip()
                if full_text:
                    entries.append([current_date, full_text])

            current_date = found_date
            current_text = []
            if rest_of_line:
                current_text.append(rest_of_line)
        else:
            if current_date:
                current_text.append(line)

    # --- Utolsó bejegyzés mentése ---
    if current_date and current_text:
        full_text = " ".join(current_text).strip()
        if full_text:
            entries.append([current_date, full_text])

    # --- CSV fájl kiírása ---
    with open(output_filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerows(entries)

    return True

# ----- Teszt -----
# if __name__ == "__main__":
#     input_file = 'log_for_hrtm1.txt'
#     output_file = 'output.csv'
#
#     if download_log("HRTM1", input_file):
#         convert_to_csv(input_file, output_file)
