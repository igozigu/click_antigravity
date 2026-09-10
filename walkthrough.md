# Antigravity 2.0 폴더 우클릭 자동 프로젝트 생성 이식 가이드

이 문서는 현재 PC에서 구현한 **"폴더 우클릭 시 Antigravity 2.0이 실행되면서 자동으로 좌측 Projects에 프로젝트가 생성·선택되는 기능"**을, 다른 Windows PC에서도 시행착오 없이 이식하기 위한 완전 가이드입니다.

목표 배포 형태는 다음과 같습니다.

- 프로젝트(또는 USB/공유 폴더) **최상위에 `AntigravityOpen.exe` 하나**만 둔다.
- 그 EXE를 **더블클릭하는 순간** 현재 PC에 컨텍스트 메뉴·브리지·경로 감지가 즉시 설치된다.
- 이후 탐색기에서 폴더/빈 배경/드라이브를 우클릭하면 **"Antigravity 2.0으로 열기"**가 나오고, 클릭 즉시 공식 Electron 앱이 활성화되며 해당 폴더가 프로젝트로 등록·선택된다.

이 문서는 사람용 설명서인 동시에, **AI 에이전트에게 한 번의 프롬프트로 앱을 만들게 하는 작업지시서**입니다.

---

## 1. 한 줄 요약

`Antigravity.exe "%V"`처럼 CLI로 폴더를 넘기는 방식은 **실패**합니다. Antigravity 2.0은 폴더 인자를 프로젝트로 등록하는 CLI가 없고, Windows 포커스 정책 때문에 창도 안 올라옵니다. 성공하려면 **CDP(DevToolsActivePort)로 React `projectManagementFeature`를 직접 호출**하는 무음 브리지가 필요합니다. 최종 산출물은 Python이 없는 PC에서도 동작하도록 **단일 EXE**로 패키징합니다.

---

## 2. 시행착오 분석 및 핵심 원리

다른 PC나 새로운 AI 에이전트가 이 작업을 수행할 때 반드시 알아야 하는 기술적 배경입니다.

### 2.1 흔히 겪는 시행착오

**Antigravity IDE vs Antigravity 2.0 혼동**

- `Antigravity IDE.exe`는 VS Code 기반이라 CLI 인자(`%V`)로 폴더를 바로 열 수 있습니다.
- 사용자가 원하는 것은 공식 독립형 Electron 앱 **Antigravity 2.0** (`Antigravity.exe`)입니다.
- IDE용 레지스트리를 2.0에 그대로 이식하면 "메뉴는 보이는데 아무 일도 없음"이 됩니다.

**단순 레지스트리 등록 시 아무 일도 일어나지 않음**

- `Antigravity.exe "%V"`로 등록하면 Electron이 second-instance 이벤트는 받을 수 있습니다.
- 그러나 폴더 인자를 파싱해 프로젝트를 만드는 CLI가 **내장되어 있지 않아 인자를 무시**합니다.
- Windows Focus Stealing Prevention 때문에 창이 위로 뜨지 않고 작업표시줄만 깜빡입니다.

**PC마다 다른 경로 (하드코딩 문제)**

- 사용자 계정명(`C:\Users\<username>`), Python 경로, Antigravity 설치 경로는 PC마다 다릅니다.
- `C:\Users\hyungjo\...` 같은 고정 경로를 쓰면 다른 PC에서 100% 실패합니다.
- 반드시 `%LOCALAPPDATA%`, `%APPDATA%`, `Path.home()`, 그리고 PyInstaller라면 `sys.executable` / `sys._MEIPASS`로 동적 감지해야 합니다.

**콘솔 창이 번쩍임**

- `python.exe`로 연결하면 우클릭마다 검은 CMD가 뜹니다.
- 개발 단계에서는 `pythonw.exe`를 쓰고, 배포 단계에서는 `--noconsole` EXE를 씁니다.

**Antigravity IDE와의 공존**

- `Antigravity IDE`(`Antigravity IDE.exe`)는 VS Code 기반의 독립된 별도 제품입니다.
- `Antigravity 2.0`(`Antigravity.exe`) 우클릭 메뉴(`Antigravity2`)와 `Antigravity IDE` 우클릭 메뉴(`AntigravityIDE`)는 서로 다른 고유 키를 사용하여 공존해야 하며, 기존 `AntigravityIDE` 키를 임의로 삭제하지 않습니다.

### 2.2 성공의 핵심 원리

```text
탐색기 우클릭
    → HKCU shell command가 AntigravityOpen.exe "%V" 실행
        → (필요 시) Antigravity.exe 기동
        → %APPDATA%\antigravity\DevToolsActivePort 에서 포트 읽기
        → http://127.0.0.1:<port>/json 에서 page WebSocket URL 획득
        → CDP: Page.bringToFront
        → CDP: Runtime.evaluate 로 React Fiber 트리를 걸어
              projectManagementFeature 를 찾음
        → 이미 같은 folderUri 프로젝트가 있으면 재사용
        → 없으면 resolveFolder 로 Git/일반 폴더 판별 후 createProject
        → window.__TSR_ROUTER__.navigate({ to: '/', search: { section: targetId } })
        → Antigravity.exe 를 한 번 더 호출해 창 활성화
```

핵심 포인트 네 가지입니다.

1. **CDP 연동**: Antigravity 2.0은 내부적으로 DevTools 포트(`%APPDATA%\antigravity\DevToolsActivePort`)를 열어 둡니다.
2. **React 내부 서비스 제어**: WebSocket으로 `projectManagementFeature`의 `resolveFolder` / `createProject`를 직접 호출합니다.
3. **TanStack Router 화면 이동**: `window.__TSR_ROUTER__.navigate({ to: '/', search: { section: targetId } })`로 방금 만든/찾은 프로젝트를 즉시 선택합니다.
4. **무음 실행**: 설치 후 우클릭 경로는 콘솔 없이 0.5~2초 안에 끝납니다.

### 2.3 하지 말아야 할 것

- `Antigravity IDE.exe`를 대상에 넣지 말 것.
- `Antigravity.exe "%1"` / `"%V"`만 레지스트리에 넣지 말 것.
- 사용자 홈 경로, Python 경로, 앱 경로를 소스에 하드코딩하지 말 것.
- HKLM(관리자 권한)에 쓰지 말 것. **HKCU만** 사용합니다. 일반 사용자 권한으로 충분합니다.
- 설치 EXE를 프로젝트 폴더에만 남겨 두고 레지스트리가 그 경로를 가리키게 하지 말 것. 폴더를 옮기면 메뉴가 깨집니다. 설치 시 **안정 경로로 자기 자신을 복사**해야 합니다.

안정 설치 경로:

```text
%USERPROFILE%\.gemini\antigravity\AntigravityOpen.exe
```

브리지 스크립트를 따로 둘 경우(개발/디버그용):

```text
%USERPROFILE%\.gemini\antigravity\open_in_antigravity.pyw
```

---

## 3. 목표 동작과 산출물

### 3.1 사용자 관점

1. 아무 Windows PC에 `AntigravityOpen.exe`를 폴더 최상위에 복사한다.
2. EXE를 더블클릭한다.
3. "설치 완료" 메시지 후, 탐색기에서 폴더 우클릭 시 **Antigravity 2.0으로 열기**가 보인다.
4. 클릭하면 콘솔 없이 Antigravity 2.0이 앞으로 오고, 좌측 Projects에 그 폴더가 생성·선택된다.
5. 같은 EXE를 `--uninstall`로 실행하면 메뉴가 제거된다.

### 3.2 에이전트가 만들어야 할 파일

프로젝트 루트 권장 구조:

```text
antigravity-open/
├── walkthrough.md                  (이 문서)
├── README.md
├── requirements.txt
├── antigravity_open.py             (설치 + 우클릭 브리지 단일 모듈)
├── build_exe.ps1                   (PyInstaller 원클릭 빌드)
└── dist/
    └── AntigravityOpen.exe         (최종 배포본, 폴더 최상위에 두면 됨)
```

`requirements.txt`:

```text
websockets>=12.0
pyinstaller>=6.0
```

### 3.3 EXE 동작 분기

| 실행 방식 | 동작 |
| --- | --- |
| 인자 없음 또는 `--install` | 자기 자신을 `%USERPROFILE%\.gemini\antigravity\`에 복사하고 HKCU 컨텍스트 메뉴 등록. 성공/실패를 MessageBox로 표시. |
| 폴더 경로 1개 (`%V`) | 무음. Antigravity 2.0을 띄우고 CDP로 프로젝트 생성/선택. |
| `--uninstall` | HKCU 키 삭제. 안정 경로의 EXE는 남겨도 되고 지워도 됨. |
| `--status` | Antigravity.exe 존재, DevTools 포트, 레지스트리 상태를 MessageBox로 표시. |

탐색기 매크로:

- 폴더 아이콘 우클릭: `%V` = 그 폴더 경로
- 폴더 내부 빈 배경 우클릭: `%V` = 현재 디렉터리
- 드라이브 우클릭: `%V` = `D:\` 형태

---

## 4. AI 에이전트용 프롬프트

아래 프롬프트는 **그대로 복사**해 Antigravity 2.0(또는 다른 코딩 에이전트)에 붙여 넣으면 됩니다. 한 번에 앱 구현 + EXE 빌드까지 시키는 것이 목적입니다.

### 4.1 앱을 처음부터 만들 때 (권장, 복붙용)

```text
Windows 탐색기에서 임의의 폴더, 폴더 내부 빈 배경, 드라이브를 마우스 우클릭했을 때
"Antigravity 2.0으로 열기" 메뉴가 나오게 하는 원클릭 설치 앱을 이 폴더에서 구현해라.

최종 목표는 폴더 최상위의 AntigravityOpen.exe를 더블클릭하는 순간
현재 PC에 기능이 즉시 설치되는 것이다.

[필수 산출물]
- antigravity_open.py (설치/제거/우클릭 브리지를 한 파일에 구현)
- requirements.txt
- build_exe.ps1
- README.md
- PyInstaller로 dist/AntigravityOpen.exe 빌드까지 수행

[대상 프로그램]
- 반드시 Antigravity IDE가 아니라 공식 Electron 앱 Antigravity 2.0 이어야 한다.
- 기본 경로: %LOCALAPPDATA%\Programs\antigravity\Antigravity.exe
- 파일이 없으면 일반적인 설치 위치를 추가로 탐색하되, 사용자 계정명을 하드코딩하지 마라.

[CLI 인자 한계]
- Antigravity.exe "%V" 만 레지스트리에 등록하면 실패한다.
- Electron second-instance는 폴더 인자를 프로젝트로 등록하지 않고, Windows 포커스 정책 때문에 창도 안 올라온다.
- 반드시 Antigravity 2.0의 CDP(%APPDATA%\antigravity\DevToolsActivePort)와
  React 내부 projectManagementFeature 를 연동하는 브리지를 구현하라.

[브리지 동작]
1. 앱이 꺼져 있으면 Antigravity.exe를 실행하고 DevToolsActivePort가 생길 때까지 최대 15초 대기.
2. 포트 파일 첫 줄의 포트로 http://127.0.0.1:<port>/json 을 읽어 type=page 인 webSocketDebuggerUrl 을 얻는다.
3. WebSocket으로 Page.bringToFront 후 Runtime.evaluate(awaitPromise=true) 실행.
4. JS에서 #root 의 React Fiber를 걸어 val.get('projectManagementFeature') 를 찾는다.
5. richProjectsProvider 상태에서 동일 folderUri 가 있으면 그 project.id 를 재사용.
6. 없으면 pm.resolveFolder(folderUri) 로 Git 여부를 판별해 createProject 한다.
   - Git: { case: "gitFolder", value: { folderUri, defaultBranch: "" } }
   - 일반: { case: "folderUri", value: folderUri }
7. window.__TSR_ROUTER__.navigate({ to: '/', search: { section: targetId } }) 로 화면 전환.
8. Antigravity.exe를 한 번 더 Popen 하여 창을 앞으로 가져온다.
9. 우클릭 경로에서는 콘솔/메시지박스 없이 실패해도 조용히 종료.

[EXE 동작]
- 인자 없음/--install: 자기 자신(frozen exe) 또는 브리지를
  %USERPROFILE%\.gemini\antigravity\AntigravityOpen.exe 로 복사하고 HKCU 메뉴 등록.
  완료 시 MessageBox.
- 폴더 경로 인자: 위의 CDP 브리지 무음 실행.
- --uninstall: 아래 키 삭제.
- --status: 진단 MessageBox.
- PyInstaller --onefile --noconsole --name AntigravityOpen
- websockets 를 바이너리에 포함하라. 대상 PC에 Python이 없어도 우클릭이 동작해야 한다.
- pythonw에 의존하지 마라. 배포 경로는 EXE여야 한다.

[레지스트리] HKCU만 사용.
- Software\Classes\Directory\shell\Antigravity2
- Software\Classes\Directory\Background\shell\Antigravity2
- Software\Classes\Drive\shell\Antigravity2
- 기본값: Antigravity 2.0으로 열기
- Icon: "<Antigravity.exe 경로>",0
- command: "<안정경로\AntigravityOpen.exe>" "%V"
- 기존 AntigravityIDE 키(VS Code 기반 Antigravity IDE)는 삭제하지 않고 보존.

[경로]
- LOCALAPPDATA, APPDATA, Path.home(), sys.executable, getattr(sys, 'frozen', False)만 사용.
- C:\Users\특정이름 하드코딩 금지.

[검증]
- 설치 후 폴더 우클릭 메뉴/아이콘 확인 방법을 README에 적을 것.
- 검은 콘솔이 뜨면 실패한 것이다.
- 코드는 실제로 실행 가능한 완성본이어야 하며, 주석으로만 설명하고 구현을 빼지 마라.
```

### 4.2 이미 Python이 있는 PC에서 스크립트만 설치할 때

에이전트에게 소스 생성/EXE 빌드까지 시킬 필요가 없고, 현재 PC에만 바로 심으면 될 때:

```text
Windows 탐색기에서 임의의 폴더나 폴더 내부 빈 배경을 마우스 우클릭했을 때,
"Antigravity 2.0으로 열기" 메뉴가 나오고 이를 클릭하면 Antigravity 2.0 데스크톱 앱이
활성화되면서 자동으로 좌측 사이드바에 해당 폴더가 프로젝트로 생성 및 선택되도록 설정해줘.

[구현 지침 및 주의사항]
1. 대상 프로그램: 반드시 Antigravity IDE가 아닌 공식 Electron 앱 'Antigravity 2.0'
   (%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe)이어야 함.
2. CLI 인자 한계 극복: Antigravity.exe는 명령줄로 폴더를 넘겨도 프로젝트로 자동 등록하지 못하므로,
   Antigravity 2.0의 CDP(DevToolsActivePort)와 React 내부 projectManagementFeature를 연동하는
   무음 백그라운드 브리지 스크립트(open_in_antigravity.pyw)를 작성하여 연결할 것.
3. 경로 동적 감지: PC마다 사용자 계정명과 파이썬 경로가 다르므로 하드코딩하지 말고
   환경 변수(%LOCALAPPDATA%, %APPDATA%, sys.executable)를 사용하여 동적으로 감지할 것.
4. 의존성 확인: websockets 라이브러리가 필요하므로 없을 경우 pip install websockets 로 자동 설치할 것.
5. 무음 실행: 우클릭 실행 시 검은 콘솔창이 뜨지 않도록 pythonw.exe 로 실행되게 구성할 것.
6. 레지스트리 등록:
   - HKCU\Software\Classes\Directory\shell\Antigravity2 (폴더 우클릭)
   - HKCU\Software\Classes\Directory\Background\shell\Antigravity2 (빈 배경 우클릭)
   - HKCU\Software\Classes\Drive\shell\Antigravity2 (드라이브 우클릭)
   - 아이콘: Antigravity.exe,0
   - 기존 Antigravity IDE 레지스트리 키(AntigravityIDE)는 별개 앱이므로 삭제하지 않고 보존할 것.
```

4.1이 **이식/배포용**, 4.2가 **현재 PC 즉시 설정용**입니다. 다른 PC에 들고 다닐 EXE를 만들려면 4.1을 사용하십시오.

---

## 5. 구현 상세

에이전트가 아래 코드를 기준으로 구현하면 됩니다. 핵심은 **한 파일에 install / uninstall / open을 모두 넣는 것**입니다. 설치 EXE와 우클릭 EXE가 분리되면 경로가 어긋나기 쉽습니다.

### 5.1 `antigravity_open.py` 전체 구현

아래는 배포용 완성 초안입니다. 에이전트는 이 동작을 빠짐없이 유지한 채, 필요하면 탐색 경로만 보강하면 됩니다.

```python
# antigravity_open.py
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.request
import winreg

INSTALL_DIRNAME = pathlib.Path.home() / ".gemini" / "antigravity"
INSTALL_EXE_NAME = "AntigravityOpen.exe"
MENU_TEXT = "Antigravity 2.0으로 열기"
SHELL_KEY = "Antigravity2"

REG_TARGETS = [
    r"Software\Classes\Directory\shell",
    r"Software\Classes\Directory\Background\shell",
    r"Software\Classes\Drive\shell",
]


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def local_appdata() -> pathlib.Path:
    return pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home() / "AppData" / "Local"))


def roaming_appdata() -> pathlib.Path:
    return pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home() / "AppData" / "Roaming"))


def find_antigravity_exe() -> pathlib.Path | None:
    candidates = [
        local_appdata() / "Programs" / "antigravity" / "Antigravity.exe",
        pathlib.Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Antigravity" / "Antigravity.exe",
        pathlib.Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Antigravity" / "Antigravity.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def port_file() -> pathlib.Path:
    return roaming_appdata() / "antigravity" / "DevToolsActivePort"


def message_box(text: str, title: str = "Antigravity 2.0", error: bool = False) -> None:
    import ctypes

    flags = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(0, text, title, flags)


def current_executable() -> pathlib.Path:
    if is_frozen():
        return pathlib.Path(sys.executable)
    return pathlib.Path(__file__).resolve()


def installed_exe_path() -> pathlib.Path:
    return INSTALL_DIRNAME / INSTALL_EXE_NAME


def ensure_app_running(app_path: pathlib.Path) -> None:
    if port_file().is_file():
        return
    subprocess.Popen([str(app_path)], close_fds=True)
    for _ in range(30):
        time.sleep(0.5)
        if port_file().is_file():
            return


def get_debugger_url() -> str | None:
    for _ in range(20):
        pf = port_file()
        if pf.is_file():
            try:
                lines = [ln.strip() for ln in pf.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
                if not lines:
                    time.sleep(0.5)
                    continue
                port = int(lines[0])
                url = f"http://127.0.0.1:{port}/json"
                with urllib.request.urlopen(url, timeout=2) as resp:
                    pages = json.loads(resp.read().decode("utf-8"))
                for page in pages:
                    if page.get("type") == "page" and page.get("webSocketDebuggerUrl"):
                        return page["webSocketDebuggerUrl"]
            except Exception:
                pass
        time.sleep(0.5)
    return None


JS_TEMPLATE = r"""
window.__openInAntigravityPromise = (async (folderUri, folderName) => {
    try {
        const root = document.querySelector('#root');
        if (!root) return JSON.stringify({ error: "No root element" });
        const fiberKey = Object.keys(root).find(k => k.startsWith('__reactContainer$'));
        const fiber = root[fiberKey];

        let pm = null;
        function walk(node, depth = 0) {
            if (!node || depth > 80 || pm) return;
            const val = node.memoizedProps && node.memoizedProps.value;
            if (val && typeof val.get === 'function') {
                try {
                    const feature = val.get('projectManagementFeature');
                    if (feature) {
                        pm = feature;
                        return;
                    }
                } catch (e) {}
            }
            walk(node.child, depth + 1);
            walk(node.sibling, depth + 1);
        }
        walk(fiber);

        if (!pm) return JSON.stringify({ error: "No projectManagementFeature found" });

        const richState = pm.richProjectsProvider && pm.richProjectsProvider.getState
            ? pm.richProjectsProvider.getState()
            : null;
        let existingId = null;
        if (richState) {
            for (const item of richState.values()) {
                const res = (item.project && item.project.projectResources && item.project.projectResources.resources) || [];
                for (const r of res) {
                    const uri = (r.type && r.type.value && r.type.value.folderUri) || (r.type && r.type.value);
                    if (uri === folderUri || decodeURIComponent(String(uri)) === folderUri) {
                        existingId = item.project.id;
                        break;
                    }
                }
                if (existingId) break;
            }
        }

        let targetId = existingId;
        if (!targetId) {
            let resolved = null;
            try {
                resolved = await pm.resolveFolder(folderUri);
            } catch (e) {}

            const isGit = resolved && (resolved.type === 1 || resolved.vcsType === 1);
            const resourceObj = isGit ? {
                case: "gitFolder",
                value: { folderUri: folderUri, defaultBranch: "" }
            } : {
                case: "folderUri",
                value: folderUri
            };

            const newId = crypto.randomUUID();
            const projectObj = {
                id: newId,
                name: folderName,
                projectResources: { resources: [{ type: resourceObj }] },
                isWorkspaceOnly: false,
                settings: {
                    fileAccessPolicy: 0,
                    internetPolicy: 0,
                    autoExecutionPolicy: 0,
                    artifactReviewMode: 0,
                    enablePermissionedGithub: false,
                    shellSetupScript: "",
                    permissionPreset: 0
                }
            };
            await pm.createProject(projectObj);
            targetId = newId;
        }

        if (window.__TSR_ROUTER__) {
            window.__TSR_ROUTER__.navigate({ to: '/', search: { section: targetId } });
        }
        return JSON.stringify({ success: true, targetId, wasExisting: !!existingId });
    } catch (err) {
        return JSON.stringify({ error: err.stack || err.message });
    }
})(FOLDER_URI_JSON, FOLDER_NAME_JSON);
window.__openInAntigravityPromise;
"""


async def setup_project_in_antigravity(ws_url: str, target_folder: str) -> dict:
    import websockets

    target_path = os.path.abspath(target_folder)
    folder_name = os.path.basename(target_path.rstrip("\\/")) or target_path
    folder_uri = pathlib.Path(target_path).as_uri()
    js_code = (
        JS_TEMPLATE
        .replace("FOLDER_URI_JSON", json.dumps(folder_uri))
        .replace("FOLDER_NAME_JSON", json.dumps(folder_name))
    )

    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Page.bringToFront"}))
        await ws.recv()
        await ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code, "awaitPromise": True},
        }))
        return json.loads(await ws.recv())


def open_folder(target_folder: str) -> None:
    app_path = find_antigravity_exe()
    if app_path is None or not os.path.exists(target_folder):
        return
    ensure_app_running(app_path)
    ws_url = get_debugger_url()
    if ws_url:
        try:
            asyncio.run(setup_project_in_antigravity(ws_url, target_folder))
        except Exception:
            pass
    try:
        subprocess.Popen([str(app_path)], close_fds=True)
    except Exception:
        pass


def delete_reg_tree(root, path: str) -> None:
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                except OSError:
                    break
                delete_reg_tree(root, path + "\\" + sub)
        winreg.DeleteKey(root, path)
    except OSError:
        pass


def register_context_menu(command_exe: pathlib.Path, app_path: pathlib.Path) -> None:
    icon_val = f'"{app_path}",0'
    cmd_val = f'"{command_exe}" "%V"'
    for parent in REG_TARGETS:
        subkey = parent + "\\" + SHELL_KEY
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, MENU_TEXT)
            winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon_val)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey + r"\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd_val)


def install() -> None:
    app_path = find_antigravity_exe()
    if app_path is None:
        message_box(
            "Antigravity 2.0 실행 파일을 찾을 수 없습니다.\n"
            r"기본 위치: %LOCALAPPDATA%\Programs\antigravity\Antigravity.exe",
            error=True,
        )
        sys.exit(1)

    INSTALL_DIRNAME.mkdir(parents=True, exist_ok=True)
    src = current_executable()
    dest = installed_exe_path()

    if is_frozen():
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        command_exe = dest
    else:
        # 개발 모드: pythonw로 py 파일을 등록. 배포 모드에서는 이 분기가 쓰이지 않음.
        python_dir = pathlib.Path(sys.executable).parent
        pythonw = python_dir / "pythonw.exe"
        runner = pythonw if pythonw.is_file() else pathlib.Path(sys.executable)
        script_dest = INSTALL_DIRNAME / "open_in_antigravity.pyw"
        shutil.copy2(src, script_dest)
        command_exe = None
        cmd_override = f'"{runner}" "{script_dest}" "%V"'
        icon_val = f'"{app_path}",0'
        for parent in REG_TARGETS:
            subkey = parent + "\\" + SHELL_KEY
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, MENU_TEXT)
                winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon_val)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey + r"\command") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd_override)
        message_box(
            "개발 모드로 컨텍스트 메뉴를 등록했습니다.\n"
            f"브리지: {script_dest}\n"
            "배포용은 build_exe.ps1 로 EXE를 만드십시오."
        )
        return

    register_context_menu(command_exe, app_path)
    message_box(
        "설치가 완료되었습니다.\n\n"
        "파일 탐색기에서 폴더를 우클릭한 뒤\n"
        "'Antigravity 2.0으로 열기'를 선택하십시오."
    )


def uninstall() -> None:
    for parent in REG_TARGETS:
        delete_reg_tree(winreg.HKEY_CURRENT_USER, parent + "\\" + SHELL_KEY)
    message_box("컨텍스트 메뉴를 제거했습니다.")


def status() -> None:
    app = find_antigravity_exe()
    pf = port_file()
    dest = installed_exe_path()
    lines = [
        f"Antigravity.exe: {app if app else '없음'}",
        f"DevToolsActivePort: {'있음' if pf.is_file() else '없음'} ({pf})",
        f"설치 EXE: {'있음' if dest.is_file() else '없음'} ({dest})",
        f"frozen: {is_frozen()}",
    ]
    message_box("\n".join(lines), title="상태")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("--install", "/install"):
        install()
        return
    if args[0] in ("--uninstall", "/uninstall"):
        uninstall()
        return
    if args[0] in ("--status", "/status"):
        status()
        return
    open_folder(args[0])


if __name__ == "__main__":
    main()
```

개발 모드에서 `websockets`가 없으면 설치 시 자동 설치를 넣고 싶다면 `install()` 맨 앞에 다음을 추가합니다. **frozen EXE에서는 pip를 호출하지 마십시오.**

```python
if not is_frozen():
    try:
        import websockets  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
```

우클릭 경로(`open_folder`)에서는 `import websockets`가 `setup_project_in_antigravity` 안에서 일어납니다. EXE 빌드 시 PyInstaller hiddenimport에 `websockets`를 넣어야 합니다.

### 5.2 `build_exe.ps1`

```powershell
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

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

Write-Host "빌드 완료: $PSScriptRoot\dist\AntigravityOpen.exe"
Write-Host "이 EXE를 아무 폴더 최상위에 복사한 뒤 더블클릭하면 현재 PC에 즉시 설치됩니다."
```

### 5.3 레지스트리 값 규격

설치가 끝난 뒤 `command` 기본값은 반드시 아래 형태여야 합니다.

```text
"C:\Users\<현재사용자>\.gemini\antigravity\AntigravityOpen.exe" "%V"
```

주의:

- EXE 경로는 항상 큰따옴표로 감쌉니다. 공백 있는 계정명 대비입니다.
- `%V`도 큰따옴표로 감쌉니다.
- `%1`을 쓰지 마십시오. 폴더 배경 우클릭에서는 `%V`가 맞습니다.
- Icon은 `AntigravityOpen.exe`가 아니라 **공식 앱** `Antigravity.exe,0`을 가리킵니다. 보라색/원형 아이콘이 나와야 합니다.

### 5.4 CDP / React 호출 시 주의

- `DevToolsActivePort` 첫 줄만 포트입니다. 둘째 줄은 browser websocket path일 수 있습니다. `/json` 리스트에서 `type == "page"`인 항목을 고르십시오.
- 앱이 막 기동된 직후 `#root` Fiber가 아직 없을 수 있습니다. 필요하면 JS evaluate를 2~3회, 0.5초 간격으로 재시도하십시오.
- `projectManagementFeature`를 못 찾으면 메뉴는 동작한 것처럼 보여도 프로젝트가 안 생깁니다. `--status`로 포트 파일 존재 여부를 먼저 확인하십시오.
- 동일 `folderUri`가 이미 있으면 `createProject`를 다시 하지 말고 navigate만 합니다. 중복 프로젝트를 막기 위한 핵심입니다.
- `pathlib.Path.as_uri()`는 `file:///C:/...` 형태입니다. 기존 항목과 비교할 때 `decodeURIComponent`도 함께 보십시오.

### 5.5 창을 앞으로 가져오는 방법

우선순위:

1. CDP `Page.bringToFront`
2. `subprocess.Popen([Antigravity.exe])` 로 second-instance 활성화
3. (선택) `user32.ShowWindow` / `SetForegroundWindow`는 포커스 정책 때문에 실패할 수 있으므로 필수는 아님

우클릭 직후 작업표시줄만 깜빡이면 1+2가 빠져 있는 것입니다.

---

## 6. 에이전트 작업 순서 (Walkthrough)

에이전트 또는 사람이 이 순서대로 하면 됩니다.

### 6.1 현재 PC에서 앱을 만들 때

1. 빈 폴더를 만들고 이 `walkthrough.md`를 그 루트에 둔다.
2. 섹션 4.1 프롬프트를 에이전트에 그대로 붙여 넣는다.
3. 에이전트가 `antigravity_open.py`, `requirements.txt`, `build_exe.ps1`을 생성했는지 확인한다.
4. `build_exe.ps1`을 실행해 `dist\AntigravityOpen.exe`를 얻는다.
5. EXE를 프로젝트 폴더 최상위로 복사한다.
6. EXE를 더블클릭해 설치 MessageBox를 확인한다.
7. 섹션 8 체크리스트로 검증한다.

### 6.2 다른 PC에 이식할 때 (EXE가 이미 있을 때)

1. `AntigravityOpen.exe`만 복사한다. Python 설치 여부는 무관하다.
2. 대상 PC에 **Antigravity 2.0**이 설치되어 있어야 한다. IDE만 있으면 실패한다.
3. EXE를 아무 위치에서 더블클릭한다. 폴더 최상위여도 되고, 다운로드 폴더여도 된다.
4. 설치 프로그램이 EXE를 `%USERPROFILE%\.gemini\antigravity\`로 복사한 뒤 메뉴를 등록한다.
5. 원본 EXE는 지워도 메뉴는 유지된다. 안정 경로 사본이 남기 때문이다.

### 6.3 다른 PC에서 에이전트 프롬프트만으로 심을 때

대상 PC에 Python과 에이전트가 있다면 섹션 4.2 프롬프트만 붙여 넣으면 됩니다. EXE 빌드 없이 `pythonw` + `.pyw`로 즉시 등록됩니다. 다만 그 PC의 Python이 제거되면 우클릭이 깨지므로, **장기 이식은 EXE 방식(4.1)** 이 맞습니다.

### 6.4 제거

```text
AntigravityOpen.exe --uninstall
```

또는 개발 모드:

```text
python antigravity_open.py --uninstall
```

---

## 7. 수동 설정용 참고 (EXE 없이 Python만)

인터넷이 제한되고 PyInstaller도 없을 때, 섹션 5.1 파일을 해당 PC에서 다음으로 실행하면 개발 모드 설치가 됩니다.

```text
python antigravity_open.py --install
```

이때 레지스트리는 다음을 가리킵니다.

```text
"<pythonw.exe>" "%USERPROFILE%\.gemini\antigravity\open_in_antigravity.pyw" "%V"
```

이 모드는 **그 PC에 같은 Python이 유지될 때만** 유효합니다. 폴더 최상위 EXE 배포가 목표면 사용하지 마십시오.

---

## 8. 검증 체크리스트

설정 후 다음만 통과하면 완료입니다.

1. **우클릭 메뉴**: 탐색기에서 임의 폴더 우클릭 시 **Antigravity 2.0으로 열기**와 공식 아이콘이 보인다. 메뉴가 두 개가 아니어야 한다.
2. **배경/드라이브**: 폴더 안 빈 곳 우클릭, 드라이브 우클릭에도 같은 메뉴가 있다.
3. **무음 실행**: 클릭 시 검은 CMD가 번쩍이지 않는다.
4. **자동 프로젝트 생성**: Antigravity 2.0 창이 최상위로 오고, 좌측 Projects에 해당 폴더가 등록된다.
5. **선택/포커스**: 방금 등록한 프로젝트가 선택된 상태로 열린다. 이미 있던 프로젝트면 새로 만들지 않고 그 항목으로 이동한다.
6. **Git 폴더**: `.git`이 있는 폴더는 gitFolder로, 없는 폴더는 일반 folderUri로 들어간다.
7. **경로 독립성**: 설치에 사용한 EXE를 다른 드라이브로 옮겨도, 이미 설치된 메뉴는 `%USERPROFILE%\.gemini\antigravity\AntigravityOpen.exe`를 가리키므로 계속 동작한다.
8. **기존 메뉴 보존**: 기존 Antigravity IDE 메뉴(`AntigravityIDE`)가 삭제되지 않고 Antigravity 2.0 메뉴와 함께 공존한다.

레지스트리 확인 (PowerShell):

```powershell
Get-ItemProperty HKCU:\Software\Classes\Directory\shell\Antigravity2
Get-ItemProperty HKCU:\Software\Classes\Directory\shell\Antigravity2\command
```

---

## 9. 문제 해결

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| 메뉴가 안 보임 | HKCU 미등록, 탐색기 캐시 | `--install` 재실행 후 탐색기 재시작(`Stop-Process -Name explorer`) |
| 메뉴는 있는데 클릭해도 무반응 | IDE exe를 가리킴, 또는 command 경로 오류 | command가 안정 경로 EXE + `"%V"`인지 확인 |
| CMD가 깜빡임 | `python.exe` / console EXE | `--noconsole`로 다시 빌드. pythonw 또는 frozen EXE만 등록 |
| 작업표시줄만 깜빡임 | CDP 없이 exe만 실행 | DevToolsActivePort 존재 확인, websockets 포함 여부 확인 |
| 창은 뜨는데 프로젝트가 안 생김 | Fiber/pm 탐색 실패, 앱 로딩 전 evaluate | 기동 대기 후 evaluate 재시도. Antigravity 2.0 UI 변경 시 JS 셀렉터 점검 |
| 다른 PC에서 실패 | 경로 하드코딩 | `C:\Users\...` 문자열이 소스에 없는지 검색 |
| 기존 IDE 메뉴 공존 | Antigravity IDE 함께 설치됨 | 정상 동작. 두 제품이 각각 독립된 메뉴로 표시됩니다. |
| `websockets` 오류 | hiddenimport 누락 | PyInstaller에 `--hidden-import websockets` |
| 설치 MessageBox에 앱 없음 | 2.0 미설치 또는 경로 변경 | 공식 앱 설치 후 `--status` |

디버그가 필요하면 임시로 `--console` 빌드를 만들어 `open_folder`에 로그를 남기되, 배포본은 다시 `--noconsole`이어야 합니다.

---

## 10. 에이전트 검수 기준 (DoD)

에이전트 작업이 끝나기 전에 아래를 모두 만족해야 합니다.

- [ ] 대상이 `Antigravity.exe`(2.0)이지 `Antigravity IDE.exe`가 아니다.
- [ ] 소스에 특정 사용자명 절대 경로가 없다.
- [ ] 우클릭 command가 `"<안정경로\AntigravityOpen.exe>" "%V"` 이다. (배포 모드)
- [ ] CDP + `projectManagementFeature` + `__TSR_ROUTER__.navigate`가 구현되어 있다.
- [ ] Git/일반 폴더 분기가 있다.
- [ ] 기존 프로젝트 중복 생성을 피한다.
- [ ] HKCU `Directory` / `Directory\Background` / `Drive` 세 곳 모두 등록한다.
- [ ] 기존 `AntigravityIDE` 레지스트리 키를 삭제하지 않고 보존한다.
- [ ] 폴더 최상위 EXE 더블클릭 = 즉시 설치(MessageBox).
- [ ] 우클릭 실행 = 콘솔 없음, MessageBox 없음.
- [ ] `dist\AntigravityOpen.exe`가 실제로 빌드된다.

이 문서를 프로젝트 루트에 둔 채 섹션 4.1 프롬프트만 에이전트에 전달하면, 위 DoD를 충족하는 원클릭 설치 앱을 재현할 수 있습니다.
