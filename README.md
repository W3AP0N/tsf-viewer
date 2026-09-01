# Tartalomjegyzék
* [TSF Viewer - Telepítési útmutató](#tsf-viewer---telepítési-útmutató)
   * [Alapfeltételek](#alapfeltételek)
   * [Konfigurációs fájlok](#konfigurációs-fájlok)
   * [Szükséges fájlok](#szükséges-fájlok)
   * [EXE legenerálása (Windows)](#exe-legenerálása-windows)
* [TSF Viewer - Használati útmutató](#tsf-viewer---használati-útmutató)
   * [A script futtatása](#a-script-futtatása)
   * [Fájlnév specifikációk](#fájlnév-specifikációk)
   * [Tömörítés](#tömörítés)
   * [Grafikus felület](#grafikus-felület)
      * [Csatornaváltás](#csatornaváltás)
      * [Gyorsbillentyűk](#gyorsbillentyűk)
      * [Felhasználói inputok](#felhasználói-inputok)
      * [Config fájl](#config-fájl)

# TSF Viewer - Telepítési útmutató
## Alapfeltételek
Ahhoz, hogy a scriptet futtatni lehessen, szükséges:

- A legfrissebb python verzió (de legalább Python 3.11 szükséges)
- A következő package-ek telepítése virtuális környezetben (lásd [EXE legenerálása](#exe-legenerálása-windows)):

    `pandas numpy pyqtgraph PyQt6 requests h5py`

## Konfigurációs fájlok
- A program egy `tsf_viewer_ftp.json` nevű állományból olvassa ki a log fájlok eléréséhez szükséges FTP adatokat. Ezt a program helyes működéséhez csatolnunk kell a projektmappába.
<br><br>
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

- Illetve van pár változó, aminek az értékét mi magunk is megadhatjuk.
Ezeket a `tsf_viewer_config.toml` fájl átírásával tehetjük meg. Ha hiányzik a config, a program rákérdez, hogy kívánjuk-e legenerálni.

## Szükséges fájlok
Ahhoz hogy az EXE állományt el tudjuk készíteni, ezekre lesz szükségünk:

- `tsf_viewer.py`
- `tsf_converter.py`
- `ftp_service.py`
- `tsf_viewer.spec`
- `icon.png`
- `icon.ico`

## EXE legenerálása (Windows)
1. Hozzunk létre egy virtuális python környezetet a projekt mappában:
    ```bash
    python -m venv venv
    ```
2. Győződjünk meg, hogy a mappában megtalálhatóak a [szükséges fájlok](#szükséges-fájlok).
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
- Kövessük az [EXE legenerálása](#exe-legenerálása-windows) utasításait a 4. lépésig.
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
### Config fájl
A program az első futás során legenerál egy `tsf_viewer_config.toml` fájlt,
amiben pár változó értékét személyre szabhatjuk. 
* Görbe ( `[plot]` ):
  * `font_size = 10`: A görbén megjelenő szövegek mérete.
  * `line_width = 3`: A görbe vonalvastagsága.
  * `event_marker_size = 13`: A felső X tengelyen lévő eseményjelölők mérete.
  * `occurrence_marker_color = cyan`: A földrengés kipattanást jelölő pötty színe.
  Megadható szöveges és hexadecimális formátumban is, pl. `"yellow"` vagy `"#FFFF00"`
  * `occurrence_marker_size = 8`: A földrengés kipattanást jelölő pötty mérete.
  * `show_unmatched_events = true`: Igaz, vagy hamis értéket vehet fel. Amennyiben
  igaz, a program kikeresi és megjeleníti azokat az eseményeket is, amikben egyik
  állomás vagy szenzor neve sem fordul elő. Ezeket az eseményeket narancssárga jelölők jelzik.
* Elérési út ( `[path]` ):
  * `datumok_txt = "datumok.txt"`<br>`ftp_json = "tsf_viewer_ftp.json"`: A program futásához
  szükséges fájlok elérési útjai. Alapértelmezett értékek: "datumok.txt" és "tsf_viewer_ftp.json"
  (Ebben az esetben a projekt könyvtárban keressük a fájlokat).
* Földrengés ( `[earthquake]` ):
  * `api_url = "https://geofon.gfz-potsdam.de/fdsnws/event/1/query"`: A földrengések lekérdezésére
  szolgáló API hívás elérési címe. Fontos, hogy a link `"/fdsnws/event/1/query"`-re kell végződjön.
* Tömörítés ( `[compression]` ):
  * `file_size_limit = 4`: Az ennél nagyobb TSF fájlokat a program HDF5 formátumba tömöríti.
  Érdemes a teljes RAM méretének felét megadni, GB (gigabyte) formátumban.
  Ezeket a bináris állományokat sokkal gyorsabban olvassa be a program,
  ezért a gyakran megnyitott fájlokat érdemes tömöríteni. A legegyszerűbb
  módja ennek a `file_size_limit = 0` értékre való állítása. Ilyenkor futtatás
  után a program automatikusan megkérdezi, hogy kívánjuk-e tömöríteni.
  * `h5_save_path = "*"`: A legenerált és tömörített HDF5 (`.h5`) fájlok mentési helye.
  Windowson KÖTELEZŐ ilyenkor a dupla backslash (`"\\"`) a mappák jelölésénél!
  Az elérési út végére nem kell backslash. pl. `"C:\\Users\\Public"`. Ha csillagot (`"*"`)
  adunk meg, az eredeti fájl helyére fogja végezni a tömörítést.
