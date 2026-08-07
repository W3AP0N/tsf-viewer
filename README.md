# TSF Viewer
## First steps

To run the script you will need:

1. The latest Python version

2. The following packages:

```bash
pip install pandas numpy pyqtgraph PyQt6 requests
```

3. UPX(Universal Packer for Executable) - Optional, for reduce the size of the EXE file.
- You can download it from here: https://upx.github.io/

- Put upx.exe in the folder where are the .py files, or add it in the system PATH.

## Configuration (config.json)

The program uses a config.json file, which is located in the root folder, for the connection to the server and for the FTP settings

Example:
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
## The files needed to build:

To build the EXE you need to have the following files in the project's root folder:

- tsf_viewer.py
- ftp_service.py
- tsf_viewer.spec
- icon.png
- icon.ico
- config.json

## The EXE file

You can build the EXE file (Windows only) with PyInstaller and the tsf\_viewer.spec file.

1. Open the terminal in the folder with the files
2. Run the command:

    ```bash
    pyinstaller tsf_viewer.spec
    ```
3. When the process is complete, the EXE file will be in the /dist folder as TSF\_Viewer.exe

If you have set upx=True in the .spec file, but you do not have upx.exe in the folder, PyInstaller will show a warning, and it will create a non-packed EXE file.
