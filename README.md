# TSF Viewer - Telepítési útmutató
## Alapfeltételek
Ahhoz hogy a scriptet futtatni lehessen, szükséges:

1. A legfrissebb python verzió
2. És a következő package-ek telepítése virtuális környezetben (lásd [EXE legenerálása](exe)):
`pandas numpy pyqtgraph PyQt6 requests h5py`

## Konfigurációs fájlok (`tsf_viewer_ftp.json`, `tsf_viewer_config.toml`)
A program egy `tsf_viewer_ftp.json` nevű állományból olvassa ki a log fájlok eléréséhez szükséges FTP adatokat. Ezt a program helyes működéséhez csatolnunk kell a projektmappába.

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
Ezeket a `tsf_viewer_config.toml` fájl átírásával tehetjük meg. Ha hiányzik a config, a program rákérdez, hogy kívánjuk-e legenerálni.

## <p id="fajlok">Szükséges fájlok<p>
Ahhoz hogy az EXE állományt el tudjuk készíteni, ezekre lesz szükségünk:

- `tsf_viewer.py`
- `tsf_converter.py`
- `ftp_service.py`
- `tsf_viewer.spec`
- `icon.png`
- `icon.ico`

## <p id="exe">EXE legenerálása (Windows)<p>
1. Hozzunk létre egy virtuális python környezetet a projekt mappában:
    ```bash
      python -m venv venv
    ```
2. Győződjünk meg, hogy a mappában megtalálhatóak a [szükséges fájlok](fajlok).
3. Indítsuk el a virtuális környezetet:
    ```bash
        venv\Scripts\activate.bat
    ```
4. Telepítsük a szükséges package-eket:
    ```bash
        pip install pandas numpy pyqtgraph PyQt6 requests h5py pyinstaller
    ```
5. Futtassuk a következő parancsot:
   ```bash
      pyinstaller tsf_viewer.spec
   ```
6. Ha a folyamat befejeződött, az EXE fájlt a `/dist` mappában találjuk `TSF_Viewer.exe` néven.

# TSF Viewer - Használati útmutató
## A script futtatása
- Kövessük az [EXE legenerálása](exe) utasításait a 4. lépésig.
- A futtatáshoz meg kell adnunk parancssori argumentumként a beolvasandó fájl
elérési útját. Ezt megtehetjük abszolút és relatív hivatkozásokkal is. A fájl
csak `.tsf` vagy `.tsf.h5` kiterjesztésű lehet. Továbbá megadhatunk
egy második argumentumot is (nem kötelező), ami a becsült beérkezési időpontokat
jelző fájl. Itt is használhatunk abszolút és relatív hivatkozásokat, viszont
a fájl kiterjesztése csak `.earthquake.tsf` lehet.
 
    Szintaxis:
   ```bash
      python tsf_viewer.py file.tsf file.earthquake.tsf
   ```

## Fájlnév specifikációk
- Ahhoz hogy a program le tudja kérdezni az állomáshoz és a szenzorhoz
feljegyzett eseményeket, a fájl nevének elején fel kell tűntetni
őket "állomás, szenzor" sorrendben, pl.: `tpso_hrtm1_1min.tsf`
- Ha a fájlnévben található pontos dátum, a program kikeresi az összes
esemény-feljegyzés közül az aznapi eseményeket, majd megjeleníti őket
a plot bal felső sarkában. Pl.: `cobs_sop2__XE__YS_20260416.tsf`
- Amennyiben fájlnév nem tartalmaz dátumot, a program kikeresi a mérés
időintervallumában feljegyzett összes eseményt, majd a felső X tengelyre 
létrehoz mindegyiknek egy jelölőt, amikre rákattintva előhozhatjuk a
feljegyzéseket. Pl.: `tpso_hrtm1_1sec_+XN_+YE_2023.tsf`

## Tömörítés
- Amennyiben a beolvasandó fájl túl nagy, a program megkérdezi, hogy
kívánjuk-e tömöríteni. Erre azért van szükség, mert ezeknél a fájloknál
csak a beolvasás betöltené a teljes memóriát, és lefagyna a számítógép.
- Alapértelmezetten 4GB a felső határ, de ezt az értéket átírhatjuk a
`tsf_viewer_config.toml` állományban. A sokszor megnyitott fájlokat érdemes
tömöríteni, mivel majdnem a tizedére tudja ez csökkenteni a beolvasás idejét.
- A program ezeket a fájlokat bináris, `.h5` kiterjesztésre konvertálja, ami
általában 80%-os méretcsökkenést eredményez.