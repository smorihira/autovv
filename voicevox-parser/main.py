import json
import uuid
import os
import subprocess
import sys  # Pythonバージョンのチェック用
import urllib.request
import urllib.parse

# Python 3.11以上なら標準のtomllib、それ未満ならサードパーティのtomlを使う
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import toml as tomllib
    except ImportError:
        print("エラー: Python 3.11未満の環境では `pip install toml` が必要です。")
        sys.exit(1)

from pathlib import Path
from parse_input import parse_lines

# .env ファイルから環境変数を読み込む（標準ライブラリのみ）
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# 保存先
OUTPUT_DIR = Path(os.environ.get("VVPROJ_OUTPUT_DIR", "output")).expanduser()


def load_config():
    config_path = Path("characters.toml")
    if config_path.exists():
        with open(
            config_path, "rb"
        ) as f:  # tomllibはバイナリモードで開く必要があります
            return tomllib.load(f)
    return {}


# --- 以下、build_audio_item と main 関数は以前と同じ ---


VOICEVOX_API = "http://localhost:50021"


def is_engine_running():
    """VOICEVOXエンジンが起動中か確認する"""
    try:
        with urllib.request.urlopen(f"{VOICEVOX_API}/version", timeout=2) as res:
            return res.status == 200
    except Exception:
        return False


def fetch_audio_query(text, style_id):
    """VOICEVOX APIからaudio_queryを取得し、キー名をcamelCaseに変換する"""
    params = urllib.parse.urlencode({"text": text, "speaker": style_id})
    url = f"{VOICEVOX_API}/audio_query?{params}"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read())
            return _snake_to_camel(data)
    except Exception as e:
        print(f"警告: audio_query取得失敗 ({text[:20]}...): {e}")
        return None


def _snake_to_camel(obj):
    """snake_caseのキーをcamelCaseに再帰的に変換し、null値を除去する"""
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


def build_audio_item(parsed_data, config):
    char_key = parsed_data["type"]
    char_conf = config.get(
        char_key, config.get("default", {"style_id": 3, "speed": 1.0})
    )

    style_id = char_conf.get("style_id", 3)
    speaker_uuid = char_conf.get("speaker_uuid", "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff")
    audio_key = str(uuid.uuid4())

    query = fetch_audio_query(parsed_data["text"], style_id)
    if query:
        query["speedScale"] = float(char_conf.get("speed", 1.0))
        query["prePhonemeLength"] = parsed_data["pre_pause"]
        query["postPhonemeLength"] = parsed_data["post_pause"]

    item = {
        "text": parsed_data["text"],
        "voice": {
            "engineId": "074fc39e-678b-4c13-8916-ffca8d505d1d",
            "speakerId": speaker_uuid,
            "styleId": style_id,
        },
    }
    if query:
        item["query"] = query

    return audio_key, item


def main():
    config = load_config()

    plot_file = Path(__file__).parent / "plot.txt"
    if not plot_file.exists():
        print("エラー: plot.txt が見つかりません。")
        return

    print(f"plot.txt を読み込み中...")
    # エンジンが起動していなければエンジンのみバックグラウンドで起動
    engine_proc = None
    if not is_engine_running():
        print("VOICEVOXエンジンが見つかりません。エンジンを起動します...")
        engine_path = "/Applications/VOICEVOX.app/Contents/Resources/vv-engine/run"
        engine_proc = subprocess.Popen(
            [engine_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import time

        for i in range(30):
            time.sleep(2)
            if is_engine_running():
                print("VOICEVOXエンジンが起動しました。")
                break
        else:
            print("警告: エンジンの起動を確認できませんでした。queryなしで続行します。")
    lines = plot_file.read_text(encoding="utf-8").splitlines()
    parsed_items = parse_lines(lines)

    if not parsed_items:
        print("データがないため終了します。")
        return

    project_name = input("プロジェクト名を入力してください: ").strip()
    if not project_name:
        project_name = "untitled"

    audio_keys = []
    audio_items = {}
    for item in parsed_items:
        key, audio_item = build_audio_item(item, config)
        audio_keys.append(key)
        audio_items[key] = audio_item

    song_track_key = str(uuid.uuid4())
    vvproj_data = {
        "appVersion": "0.24.0",
        "talk": {
            "audioKeys": audio_keys,
            "audioItems": audio_items,
        },
        "song": {
            "tpqn": 480,
            "tempos": [{"position": 0, "bpm": 120}],
            "timeSignatures": [{"measureNumber": 1, "beats": 4, "beatType": 4}],
            "tracks": {
                song_track_key: {
                    "name": "無名トラック",
                    "keyRangeAdjustment": 0,
                    "volumeRangeAdjustment": 0,
                    "notes": [],
                    "pitchEditData": [],
                    "volumeEditData": [],
                    "phonemeTimingEditData": {},
                    "solo": False,
                    "mute": False,
                    "gain": 1,
                    "pan": 0,
                }
            },
            "trackOrder": [song_track_key],
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_path = OUTPUT_DIR / f"{project_name}.vvproj"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(vvproj_data, f, ensure_ascii=False, indent=2)

    print(f"プロジェクトを作成しました: {file_path}")

    try:
        if os.name == "posix":  # macOS
            import time

            # VOICEVOXが起動中なら終了してから開き直す
            subprocess.run(
                ["osascript", "-e", 'quit app "VOICEVOX"'],
                stderr=subprocess.DEVNULL,
            )
            # プロセスが完全に終了するまで待機（保存ダイアログ対応）
            for _ in range(30):
                result = subprocess.run(
                    ["pgrep", "-x", "VOICEVOX"],
                    capture_output=True,
                )
                if result.returncode != 0:
                    break
                time.sleep(1)
            else:
                print("警告: VOICEVOXの終了を確認できませんでした。")
            # スクリプトが起動したエンジンプロセスを停止（GUIが自前のエンジンを起動する）
            if engine_proc is not None:
                engine_proc.terminate()
                engine_proc.wait(timeout=5)
            time.sleep(1)
            subprocess.run(["open", "-a", "VOICEVOX", str(file_path)])
        else:  # Windows
            os.startfile(str(file_path))
    except Exception as e:
        print(f"VOICEVOXの起動に失敗しました: {e}")


if __name__ == "__main__":
    main()
