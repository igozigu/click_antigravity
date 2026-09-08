# antigravity_open.py
# Antigravity 2.0 폴더 우클릭 → 프로젝트 자동 생성 브리지
# 설치 / 제거 / 우클릭 핸들러를 한 파일에 포함
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

# ── 상수 ──────────────────────────────────────────────
INSTALL_DIRNAME = pathlib.Path.home() / ".gemini" / "antigravity"
INSTALL_EXE_NAME = "AntigravityOpen.exe"
MENU_TEXT = "Antigravity 2.0으로 열기"
SHELL_KEY = "Antigravity2"
LEGACY_KEY = "AntigravityIDE"

REG_TARGETS = [
    r"Software\Classes\Directory\shell",
    r"Software\Classes\Directory\Background\shell",
    r"Software\Classes\Drive\shell",
]


# ── 유틸 ──────────────────────────────────────────────
def is_frozen() -> bool:
    """PyInstaller frozen 여부"""
    return bool(getattr(sys, "frozen", False))


def local_appdata() -> pathlib.Path:
    return pathlib.Path(
        os.environ.get("LOCALAPPDATA", pathlib.Path.home() / "AppData" / "Local")
    )


def roaming_appdata() -> pathlib.Path:
    return pathlib.Path(
        os.environ.get("APPDATA", pathlib.Path.home() / "AppData" / "Roaming")
    )


def find_antigravity_exe() -> pathlib.Path | None:
    """Antigravity 2.0 실행 파일을 동적으로 탐색"""
    candidates = [
        local_appdata() / "Programs" / "antigravity" / "Antigravity.exe",
        pathlib.Path(
            os.environ.get("PROGRAMFILES", r"C:\Program Files")
        )
        / "Antigravity"
        / "Antigravity.exe",
        pathlib.Path(
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        )
        / "Antigravity"
        / "Antigravity.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def port_file() -> pathlib.Path:
    """CDP DevToolsActivePort 경로"""
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


# ── CDP 헬퍼 ──────────────────────────────────────────
def ensure_app_running(app_path: pathlib.Path) -> None:
    """Antigravity 2.0이 안 떠 있으면 기동하고 포트 파일 대기 (최대 15초)"""
    if port_file().is_file():
        return
    subprocess.Popen([str(app_path)], close_fds=True)
    for _ in range(30):
        time.sleep(0.5)
        if port_file().is_file():
            return


def get_debugger_url() -> str | None:
    """DevToolsActivePort에서 포트를 읽고, /json 에서 page WS URL을 반환"""
    for _ in range(20):
        pf = port_file()
        if pf.is_file():
            try:
                lines = [
                    ln.strip()
                    for ln in pf.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if ln.strip()
                ]
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


# ── React/CDP JS ──────────────────────────────────────
JS_TEMPLATE = r"""
window.__openInAntigravityPromise = (async (folderUri, folderName) => {
    // 앱이 완전히 로드될 때까지 최대 3회 재시도
    for (let attempt = 0; attempt < 3; attempt++) {
        try {
            const root = document.querySelector('#root');
            if (!root) {
                await new Promise(r => setTimeout(r, 500));
                continue;
            }
            const fiberKey = Object.keys(root).find(k => k.startsWith('__reactContainer$'));
            if (!fiberKey) {
                await new Promise(r => setTimeout(r, 500));
                continue;
            }
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

            if (!pm) {
                await new Promise(r => setTimeout(r, 500));
                continue;
            }

            // 기존 프로젝트 중복 확인
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
                // Git/일반 폴더 판별
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

            // TanStack Router로 화면 이동
            if (window.__TSR_ROUTER__) {
                window.__TSR_ROUTER__.navigate({ to: '/', search: { section: targetId } });
            }
            return JSON.stringify({ success: true, targetId, wasExisting: !!existingId });
        } catch (err) {
            if (attempt < 2) {
                await new Promise(r => setTimeout(r, 500));
                continue;
            }
            return JSON.stringify({ error: err.stack || err.message });
        }
    }
    return JSON.stringify({ error: "Failed after retries" });
})(FOLDER_URI_JSON, FOLDER_NAME_JSON);
window.__openInAntigravityPromise;
"""


async def setup_project_in_antigravity(ws_url: str, target_folder: str) -> dict:
    """WebSocket으로 CDP 세션을 열고, React 내부 projectManagementFeature를 조작"""
    import websockets

    target_path = os.path.abspath(target_folder)
    folder_name = os.path.basename(target_path.rstrip("\\/")) or target_path
    folder_uri = pathlib.Path(target_path).as_uri()
    js_code = (
        JS_TEMPLATE.replace("FOLDER_URI_JSON", json.dumps(folder_uri)).replace(
            "FOLDER_NAME_JSON", json.dumps(folder_name)
        )
    )

    async with websockets.connect(ws_url) as ws:
        # 1) 창을 앞으로
        await ws.send(json.dumps({"id": 1, "method": "Page.bringToFront"}))
        await ws.recv()
        # 2) React Fiber → projectManagementFeature → createProject / navigate
        await ws.send(
            json.dumps(
                {
                    "id": 2,
                    "method": "Runtime.evaluate",
                    "params": {"expression": js_code, "awaitPromise": True},
                }
            )
        )
        return json.loads(await ws.recv())


# ── 우클릭 핸들러 ─────────────────────────────────────
def open_folder(target_folder: str) -> None:
    """무음. 탐색기 우클릭 시 호출되며, 실패해도 조용히 종료."""
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
    # Antigravity.exe를 한 번 더 Popen → second-instance 로 창 활성화
    try:
        subprocess.Popen([str(app_path)], close_fds=True)
    except Exception:
        pass


# ── 레지스트리 ────────────────────────────────────────
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


def cleanup_legacy() -> None:
    """한글 깨진 AntigravityIDE 레거시 키 삭제"""
    for parent in REG_TARGETS:
        delete_reg_tree(winreg.HKEY_CURRENT_USER, parent + "\\" + LEGACY_KEY)


# ── 설치 / 제거 / 상태 ───────────────────────────────
def install() -> None:
    # 개발 모드에서 websockets 자동 설치
    if not is_frozen():
        try:
            import websockets  # noqa: F401
        except ImportError:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "websockets"]
            )

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
        # ── 배포(EXE) 모드 ──
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        command_exe = dest
        cleanup_legacy()
        register_context_menu(command_exe, app_path)
        message_box(
            "설치가 완료되었습니다.\n\n"
            "파일 탐색기에서 폴더를 우클릭한 뒤\n"
            "'Antigravity 2.0으로 열기'를 선택하십시오."
        )
    else:
        # ── 개발(Python) 모드 ──
        python_dir = pathlib.Path(sys.executable).parent
        pythonw = python_dir / "pythonw.exe"
        runner = pythonw if pythonw.is_file() else pathlib.Path(sys.executable)
        script_dest = INSTALL_DIRNAME / "open_in_antigravity.pyw"
        shutil.copy2(src, script_dest)
        cmd_override = f'"{runner}" "{script_dest}" "%V"'
        icon_val = f'"{app_path}",0'
        cleanup_legacy()
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


def uninstall() -> None:
    for parent in REG_TARGETS:
        delete_reg_tree(winreg.HKEY_CURRENT_USER, parent + "\\" + SHELL_KEY)
        delete_reg_tree(winreg.HKEY_CURRENT_USER, parent + "\\" + LEGACY_KEY)
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


# ── 진입점 ────────────────────────────────────────────
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
    # 폴더 경로가 넘어온 경우 → 우클릭 브리지 (무음)
    open_folder(args[0])


if __name__ == "__main__":
    main()
