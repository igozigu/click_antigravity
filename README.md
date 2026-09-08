# AntigravityOpen

Windows 탐색기 우클릭으로 **Antigravity 2.0**에 폴더를 프로젝트로 등록·선택하는 원클릭 설치 앱입니다.

## 사용법

### 설치 (EXE)

1. `AntigravityOpen.exe`를 아무 위치에 둡니다.
2. **더블클릭**합니다.
3. "설치 완료" 메시지가 뜨면 탐색기에서 폴더를 우클릭하세요.
4. **"Antigravity 2.0으로 열기"** 메뉴가 나옵니다.

### 설치 (Python 개발 모드)

```powershell
python antigravity_open.py --install
```

### 제거

```powershell
AntigravityOpen.exe --uninstall
# 또는
python antigravity_open.py --uninstall
```

### 상태 확인

```powershell
AntigravityOpen.exe --status
```

## EXE 빌드

```powershell
.\build_exe.ps1
```

빌드 결과: `dist\AntigravityOpen.exe`

## 동작 원리

| 단계 | 설명 |
| --- | --- |
| 1 | 탐색기 우클릭 시 HKCU 레지스트리의 shell command가 `AntigravityOpen.exe "%V"` 실행 |
| 2 | Antigravity 2.0이 꺼져 있으면 자동 기동, DevToolsActivePort 대기 |
| 3 | CDP(Chrome DevTools Protocol)로 WebSocket 연결 |
| 4 | React Fiber 트리에서 `projectManagementFeature` 탐색 |
| 5 | 이미 등록된 폴더면 해당 프로젝트로 이동, 없으면 Git/일반 분기 후 신규 생성 |
| 6 | `Page.bringToFront` + second-instance로 창 활성화 |

## 요구 사항

- **Antigravity 2.0** (공식 Electron 앱)이 설치되어 있어야 합니다.
  - 기본 경로: `%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe`
- EXE 배포 시 대상 PC에 Python은 필요 없습니다.

## 검증

```powershell
# 레지스트리 확인
Get-ItemProperty HKCU:\Software\Classes\Directory\shell\Antigravity2
Get-ItemProperty HKCU:\Software\Classes\Directory\shell\Antigravity2\command
```

- 폴더/빈 배경/드라이브 우클릭에 메뉴와 아이콘이 보여야 합니다.
- 클릭 시 검은 CMD가 뜨면 안 됩니다.
- Antigravity 2.0 좌측 Projects에 해당 폴더가 등록·선택되어야 합니다.

## 파일 구조

```
├── antigravity_open.py      설치/제거/우클릭 브리지 (단일 모듈)
├── build_exe.ps1            PyInstaller 원클릭 빌드
├── requirements.txt         Python 의존성
├── README.md                이 파일
├── walkthrough.md           상세 기술 가이드
└── dist/
    └── AntigravityOpen.exe  최종 배포본
```
