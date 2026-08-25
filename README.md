# TSF Viewer - Telepítési útmutató
## Alapfeltételek
Ahhoz, hogy a scriptet futtatni lehessen, szükséges:

1. A legfrissebb python verzió
2. És a következő package-ek telepítése virtuális környezetben (lásd [EXE legenerálása](#exe)):
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

## <p id="fajlok">Szükséges fájlok</p>
Ahhoz hogy az EXE állományt el tudjuk készíteni, ezekre lesz szükségünk:

- `tsf_viewer.py`
- `tsf_converter.py`
- `ftp_service.py`
- `tsf_viewer.spec`
- `icon.png`
- `icon.ico`

## <p id="exe">EXE legenerálása (Windows)</p>
1. Hozzunk létre egy virtuális python környezetet a projekt mappában:
    ```bash
      python -m venv venv
    ```
2. Győződjünk meg, hogy a mappában megtalálhatóak a [szükséges fájlok](#fajlok).
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
- Kövessük az [EXE legenerálása](#exe) utasításait a 4. lépésig.
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
- Amennyiben a fájlnév nem tartalmaz dátumot, a program kikeresi a mérés
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

## Grafikus felület
Ha beolvastuk a fájlt és betöltött a program, az első csatorna
görbéje fog fogadni minket. Amennyiben a fájlban vannak hiányzó
adatok, a program vörös háttérrel fogja jelezni őket.
### Csatornaváltás
- Csatornát úgy válthatunk, ha az ablak tetején lévő lenyíló listára
kattintunk. Ilyenkor legördülnek az opciók és tetszőlegesen kiválaszthatjuk
a megjelenítendő csatornát.
- Továbbá használható a billentyűzet is, amennyiben az átváltani kívánt csatorna
kezdőbetűjét lenyomjuk. Pl.: "X_tilt_(+X=tilt_to_south)" - `X`, "air_pressure" - `A`, stb..
### Gyorsbillentyűk
- A csatornaváltás lenyíló listája alatt található egy sor gomb. Mindegyikre
rá van írva a funkciója, illetve a gyorsbillentyűje.
- `[R] Reset view`: Alaphelyzetbe állítja a görbét.
- `[G] Show/hide gap borders`: Megjeleníti/elrejti az adathézagok széleit jelző vonalakat.
- `[I] Show/hide event(s)`: <br>- Ha tartalmaz dátumot a fájl, elrejti/megjeleníti az eseményleírást.
<br>- Ha nem, akkor első lenyomásra berajzolja az eseményjelölőknél függőleges vonalakat, második
lenyomásnál pedig eltünteti a jelölőt, a vonalakat és az eseményleírást is. A következő lenyomásnál
ismét megjelennek a jelölők.
- `[M] Toggle Method`: Ha beolvastunk egy becsült beérkezési időpontokat tartalmazó fájlt is, ezzel
a gombbal válthatunk a különböző számítási eljárások között.
- Ha egy funkció nem elérhető, pl. nincs az adott fájlhoz esemény, vagy nincsenek
hiányzó adatok, akkor az adott funkció elérésére szolgáló gomb inaktívra vált.
### Felhasználói inputok
- Az ábrába görgővel lehet belenagyítani. Ha valamelyik tengelyre visszük a
kurzort és ott görgetünk, azzal szét tudjuk húzni az ábrát, illetve össze is
tudjuk nyomni. Jobb egérgombot lenyomva tatva lehet mozgatni a diagramot, bal
egérgombot nyomvatartva lehet zoom-olni, összenyomni, stb..
- A plotra való bal kattintásra kiírja egy felugró ablakban az adott ponthoz
tartozó adatokat (index, dátum, időbélyeg, mértékegység, stb..).
- Ha lenyomva tartjuk az `E` billentyűt, majd bal egérgombbal kattintunk,
lekérdezi alapértelmezetten a https://geofon.gfz-potsdam.de weboldaláról
az adott időpillanathoz tartozó földrengés adatokat. A webcím módosítható
a `tsf_viewer_config.toml` fájlban.