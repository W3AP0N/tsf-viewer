# TSF Viewer
## Alapfeltételek

Ahoz hogy a scriptet futtatni lehessen szükséges:

1. A legfrissebb python verzió

2. És a következő package-ek telepítése:

```bash
pip install pandas numpy pyqtgraph PyQt6 requests
```

3. UPX (Universal Packer for Executable) - Nem kötelező, a script futtatható állományának generálásánal ajánlott, mert drasztikusan csökkenti a végső file méretét.
- Letöltés: https://upx.github.io/

- Ezután helyezzük az upx.exe fájlt a projektmappába

## Konfigurációs file (config.json)

A program egy config.json nevű állományból olvassa ki a log fájlok eléréséhez szükséges FTP adatokat. Ezt a program helyes működéséhez csatolnunk kell a projektmappába.

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
## Szükséges fájlok

Ahoz hogy az EXE állományt el tudjuk készíteni, ezekre lesz szükség:

- tsf_viewer.py
- ftp_service.py
- tsf_viewer.spec
- icon.png
- icon.ico
- config.json

## EXE legenerálása

A pyinstaller segítségével lehetséges. Ha még nem tettük meg, telepíthetjük az első paranncsal. Ha megvan, a második parancs végzi el az EXE elkészítését:
 
   ```bash
    pip install pyinstaller
    pyinstaller tsf_viewer.spec
   ```
Ha a folyamat befejeződött, az EXE fájlt a /dist mappában találjuk TSF_Viewer.exe néven.
