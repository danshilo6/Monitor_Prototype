import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SPEC_FILES = {
    "windows": "MonitorApp_OneDir.spec",
    "linux": "Monitor_OneDir_linux.spec",
}


def build(platform: str):
    if platform not in SPEC_FILES:
        print(f"Error: platform must be one of {list(SPEC_FILES.keys())}")
        sys.exit(1)

    today = datetime.now().strftime("%d_%m_%y")
    app_name = f"Monitor_{today}"

    project_root = Path(__file__).parent.parent
    spec_file = project_root / SPEC_FILES[platform]

    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec_file)],
        cwd=project_root,
        env={**os.environ, "APP_NAME": app_name},
        check=True,
    )

    print(f"\nBuild complete: dist/{app_name}/")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python build.py [windows|linux]")
        sys.exit(1)

    build(sys.argv[1])
