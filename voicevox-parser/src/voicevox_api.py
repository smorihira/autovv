"""VOICEVOX エンジン API 通信モジュール"""

import json
import subprocess
import time
import urllib.parse
import urllib.request

# ── 定数 ──────────────────────────────────────────────

API_BASE = "http://localhost:50021"
ENGINE_PATH = "/Applications/VOICEVOX.app/Contents/Resources/vv-engine/run"
ENGINE_STARTUP_TIMEOUT = 30  # 秒
ENGINE_POLL_INTERVAL = 2  # 秒


# ── エンジン管理 ──────────────────────────────────────


def is_engine_running() -> bool:
    """VOICEVOXエンジンが起動中か確認する"""
    try:
        with urllib.request.urlopen(f"{API_BASE}/version", timeout=2) as res:
            return res.status == 200
    except Exception:
        return False


def start_engine() -> subprocess.Popen:
    """エンジンをバックグラウンドで起動し、Popen オブジェクトを返す"""
    return subprocess.Popen(
        [ENGINE_PATH],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_engine(timeout: int = ENGINE_STARTUP_TIMEOUT) -> bool:
    """エンジンが応答するまで待機する。成功なら True。"""
    for _ in range(timeout // ENGINE_POLL_INTERVAL):
        time.sleep(ENGINE_POLL_INTERVAL)
        if is_engine_running():
            return True
    return False


def ensure_engine() -> subprocess.Popen | None:
    """
    エンジンが起動していなければ起動する。
    起動したプロセスを返す。既に起動済みなら None を返す。
    """
    if is_engine_running():
        return None

    print("VOICEVOXエンジンが見つかりません。エンジンを起動します...")
    proc = start_engine()

    if wait_for_engine():
        print("VOICEVOXエンジンが起動しました。")
    else:
        print("警告: エンジンの起動を確認できませんでした。queryなしで続行します。")

    return proc


def stop_engine(proc: subprocess.Popen) -> None:
    """エンジンプロセスを停止する"""
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ── API 呼び出し ──────────────────────────────────────


def fetch_audio_query(text: str, style_id: int) -> dict | None:
    """VOICEVOX API から audio_query を取得し、キー名を camelCase に変換する"""
    params = urllib.parse.urlencode({"text": text, "speaker": style_id})
    url = f"{API_BASE}/audio_query?{params}"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read())
            return _snake_to_camel(data)
    except Exception as e:
        print(f"警告: audio_query取得失敗 ({text[:20]}...): {e}")
        return None


def _snake_to_camel(obj):
    """snake_case のキーを camelCase に再帰的に変換し、null 値を除去する"""
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if v is None:
                continue
            parts = k.split("_")
            camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
            new[camel] = _snake_to_camel(v)
        return new
    elif isinstance(obj, list):
        return [_snake_to_camel(item) for item in obj]
    return obj
