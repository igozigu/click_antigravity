$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Antigravity Open EXE 빌드 ===" -ForegroundColor Cyan

# 의존성 설치
Write-Host "[1/3] 의존성 설치 중..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 빌드
Write-Host "[2/3] PyInstaller 빌드 중..." -ForegroundColor Yellow
python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --noconsole `
  --name AntigravityOpen `
  --hidden-import websockets `
  --hidden-import websockets.legacy `
  --hidden-import websockets.legacy.client `
  antigravity_open.py

# 결과 확인
$exe = Join-Path $PSScriptRoot "dist\AntigravityOpen.exe"
if (Test-Path $exe) {
    Write-Host "[3/3] 빌드 완료!" -ForegroundColor Green
    Write-Host "  출력: $exe" -ForegroundColor Green
    Write-Host ""
    Write-Host "사용법:" -ForegroundColor Cyan
    Write-Host "  1. $exe 를 아무 위치에 복사"
    Write-Host "  2. 더블클릭하면 현재 PC에 즉시 설치"
    Write-Host "  3. 탐색기에서 폴더 우클릭 → 'Antigravity 2.0으로 열기'"
    Write-Host ""
    Write-Host "제거: AntigravityOpen.exe --uninstall"
    Write-Host "상태: AntigravityOpen.exe --status"
} else {
    Write-Host "[ERROR] 빌드 실패 - dist\AntigravityOpen.exe 를 찾을 수 없습니다." -ForegroundColor Red
    exit 1
}
