# TSF Viewer
## Alapfeltételek
Ahhoz hogy a scriptet futtatni lehessen szükséges:

1. A legfrissebb python verzió
2. És a következő package-ek telepítése:

```bash
pip install pandas numpy pyqtgraph PyQt6 requests h5py
```

## Konfigurációs fájlok (ftp.json, config.toml)
A program egy ftp.json nevű állományból olvassa ki a log fájlok eléréséhez szükséges FTP adatokat. Ezt a program helyes működéséhez csatolnunk kell a projektmappába.

A JSON szerkezete:
```
{
    "STATION1": {
        "host": "example.server.com",
        "user": "username",
        "passwd": "password",
        "path": "/optional/folder/path/"
    },
    "STATION2": {
        "host": "example2.server.com",
        "user": "username2",
        "passwd": "password2"
    }
}
```

Illetve van pár változó, aminek az értékét mi magunk is megadhatjuk.
Ezeket a config.toml fájl átírásával tehetjük meg.

## Szükséges fájlok
Ahhoz hogy az EXE állományt el tudjuk készíteni, ezekre lesz szükségünk:

- tsf_viewer.py
- tsf_converter.py
- ftp_service.py
- tsf_viewer.spec
- icon.png
- icon.ico

## EXE legenerálása
A pyinstaller segítségével lehetséges. Ha még nem tettük meg, telepíthetjük az első paranncsal. Ha megvan, a második parancs végzi el az EXE elkészítését:

   ```bash
    pip install pyinstaller
    pyinstaller tsf_viewer.spec
   ```
Ha a folyamat befejeződött, az EXE fájlt a /dist mappában találjuk TSF_Viewer.exe néven.
UPX használható, de sokat nem változtat a végső fájlméreten, illetve sokkal lassabb lesz a betöltés is.
