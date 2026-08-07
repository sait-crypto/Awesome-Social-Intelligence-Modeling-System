# Windows Packaging

[Back to the main README](../../README.md)

The build produces a single `Submit.exe` in the repository root. The executable contains Python and the required packages, so running it does not require `.venv`, Python, or `uv sync`. It continues to read and write the repository's existing configuration, databases, update files, assets, and `.env`. It exposes the same GUI workflows as `uv run submit.py`, including creating and submitting pull requests. The pull-request workflow still requires Git and an authenticated GitHub CLI installation on the machine, exactly as the Python entry point does.

Building or rebuilding the executable requires `uv` and a working Python 3.14 installation once. The commands create an isolated packaging environment under the ignored `engineering/build/` directory and do not replace the project's normal `.venv`.

Run these commands from the repository root:

```powershell
$packagingEnvironment = 'engineering\build\package-env'
$previousUvProjectEnvironment = $env:UV_PROJECT_ENVIRONMENT
$env:UV_PROJECT_ENVIRONMENT = $packagingEnvironment

uv sync --all-groups --python '3.14' --frozen

$packagingEnvironment = (Resolve-Path $packagingEnvironment).Path
$pyinstaller = Join-Path $packagingEnvironment 'Scripts\pyinstaller.exe'
$tkinterDnd = Join-Path $packagingEnvironment 'Lib\site-packages\tkinterdnd2'

& $pyinstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --hide-console hide-early `
    --name 'Submit' `
    --distpath '.' `
    --workpath 'engineering\build\Submit' `
    --specpath 'engineering\build' `
    --paths 'engineering' `
    --collect-all 'tkinterdnd2' `
    --add-data "$tkinterDnd;tkinterdnd2" `
    --hidden-import 'src.update' `
    --hidden-import 'src.validate' `
    --hidden-import 'src.convert' `
    'submit.py'

if ($null -eq $previousUvProjectEnvironment) {
    Remove-Item Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue
} else {
    $env:UV_PROJECT_ENVIRONMENT = $previousUvProjectEnvironment
}
```

After the command succeeds, start the GUI by double-clicking `Submit.exe`. Keep the executable in the repository root; moving it elsewhere prevents it from finding the shared repository files.

The executable uses the source modules captured at build time. Rebuild it after changing application code or Python-based taxonomy configuration. Ordinary database, INI, JSON, CSV, asset, and `.env` changes do not require rebuilding.

To remove local PyInstaller work files without deleting `Submit.exe`, run:

```powershell
Remove-Item -LiteralPath '.\engineering\build\Submit' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath '.\engineering\build\Submit.spec' -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath '.\engineering\build\package-env' -Recurse -Force -ErrorAction SilentlyContinue
```

Do not commit `Submit.exe` unless the repository intentionally publishes binary releases.
