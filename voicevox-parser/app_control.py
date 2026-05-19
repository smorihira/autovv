"""VOICEVOX アプリケーション制御モジュール (macOS)"""

import os
import subprocess
import time

from voicevox_api import stop_engine

# ── 定数 ──────────────────────────────────────────────

QUIT_TIMEOUT = 30  # 秒
QUIT_POLL_INTERVAL = 1  # 秒


# ── 内部関数 ──────────────────────────────────────────


def _quit_voicevox() -> None:
    """VOICEVOX GUI に終了リクエストを送り、プロセス終了まで待機する"""
    subprocess.run(
        ["osascript", "-e", 'quit app "VOICEVOX"'],
        stderr=subprocess.DEVNULL,
    )
    for _ in range(QUIT_TIMEOUT):
        result = subprocess.run(
            ["pgrep", "-x", "VOICEVOX"],
            capture_output=True,
        )
        if result.returncode != 0:
            return
        time.sleep(QUIT_POLL_INTERVAL)

    print("警告: VOICEVOXの終了を確認できませんでした。")


def _open_with_voicevox(file_path) -> None:
    """VOICEVOX GUI でプロジェクトファイルを開く"""
    subprocess.run(["open", "-a", "VOICEVOX", str(file_path)])


# ── 公開関数 ──────────────────────────────────────────


def restart_with_project(file_path, engine_proc=None) -> None:
    """
    VOICEVOX を終了し、エンジンプロセスを停止し、
    新しいプロジェクトで VOICEVOX を開き直す。
    """
    try:
        if os.name != "posix":
            os.startfile(str(file_path))
            return

        _quit_voicevox()

        if engine_proc is not None:
            stop_engine(engine_proc)

        time.sleep(1)
        _open_with_voicevox(file_path)
    except Exception as e:
        print(f"VOICEVOXの起動に失敗しました: {e}")
