"""
Briefwave — PyInstaller 빌드 스크립트

사용법:
    pip install pyinstaller
    python build_exe.py

결과물:
    dist/Briefwave/
        Briefwave.exe   ← 실행 파일
        data/                ← 데이터 (exe 옆에 위치, 쓰기 가능)
        .env                 ← 설정 파일
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "Briefwave"


def main():
    # 1. PyInstaller 설치 확인
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. 번들에 포함할 리소스 (읽기 전용 — exe 내부에 패킹)
    datas = [
        ("index.html", "."),
        ("monitor.html", "."),
        ("health_monitor.html", "."),
        ("app.js", "."),
        ("report_monitor.js", "."),
        ("health_monitor.js", "."),
        ("monitor.js", "."),
        ("utils.js", "."),
        ("styles.css", "."),
    ]

    add_data_args = []
    sep = ";" if sys.platform == "win32" else ":"
    for src, dst in datas:
        add_data_args.extend(["--add-data", f"{src}{sep}{dst}"])

    # 3. PyInstaller 실행
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "Briefwave",
        "--onedir",
        "--noconfirm",
        "--console",                 # 콘솔 창 표시 (로그 확인용)
        "--icon", "NONE",
        *add_data_args,
        "server.py",
    ]

    print("빌드 시작...")
    print(f"  명령: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(ROOT))

    # 4. data/ 폴더를 exe 옆에 복사 (런타임 쓰기 가능해야 함)
    dist_data = DIST / "data"
    if dist_data.exists():
        shutil.rmtree(dist_data)
    shutil.copytree(ROOT / "data", dist_data)
    print(f"  data/ → {dist_data}")

    # 5. .env 복사
    env_src = ROOT / ".env"
    if not env_src.exists():
        env_src = ROOT / ".env.example"
    shutil.copy2(env_src, DIST / ".env")
    print(f"  .env → {DIST / '.env'}")

    # 6. 완료
    print()
    print("=" * 50)
    print("빌드 완료!")
    print(f"  위치: {DIST}")
    print()
    print("배포 방법:")
    print(f"  1. {DIST} 폴더를 통째로 zip 압축")
    print("  2. 테스터에게 전달")
    print("  3. 압축 해제 후 Briefwave.exe 더블클릭")
    print("  4. 브라우저에서 http://localhost:8080 접속")
    print("=" * 50)


if __name__ == "__main__":
    main()
