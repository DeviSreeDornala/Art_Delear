# build.ps1 - build one-file Windows executable using PyInstaller
# Run this from the repository root (where src/ and assets/ live)

param(
    [string]$Entry = "src\\main.py",
    [string]$Name = "ArtDealer",
    [switch]$Clean
)

if ($Clean) {
    Remove-Item -Recurse -Force dist build "$Name.spec" -ErrorAction SilentlyContinue
}

# create a virtual environment if not present
if (-not (Test-Path .venv)) {
    python -m venv .venv
}
$activate = ".\.venv\\Scripts\\Activate.ps1"
Write-Host "Activating venv and installing requirements..."
& pwsh -c "& '$activate'; pip install --upgrade pip; pip install -r requirements.txt; pip install pyinstaller"

# Build with PyInstaller. We include the assets folder as data so the onefile contains them.
$assets = "assets;assets"
# Add any additional data entries as needed
pyinstaller --noconfirm --onefile --windowed --name $Name --add-data $assets $Entry
Write-Host "Build finished. See dist\\$Name.exe"
