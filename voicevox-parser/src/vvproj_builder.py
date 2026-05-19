"""VOICEVOX プロジェクトファイル (.vvproj) 構築モジュール"""

import json
import uuid
from pathlib import Path

from src.parse_input import ParsedLine
from src.voicevox_api import fetch_audio_query

# ── 定数 ──────────────────────────────────────────────

APP_VERSION = "0.24.0"
DEFAULT_ENGINE_ID = "074fc39e-678b-4c13-8916-ffca8d505d1d"
DEFAULT_SPEAKER_UUID = "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff"


# ── 内部関数 ──────────────────────────────────────────


def _build_audio_item(parsed_data: ParsedLine, char_conf: dict) -> tuple[str, dict]:
    """ParsedLine とキャラクター設定から audio_item を構築する"""
    style_id = char_conf.get("style_id", 3)
    speaker_uuid = char_conf.get("speaker_uuid", DEFAULT_SPEAKER_UUID)
    engine_id = char_conf.get("engine_id", DEFAULT_ENGINE_ID)
    audio_key = str(uuid.uuid4())

    query = fetch_audio_query(parsed_data.text, style_id)
    if query:
        query["speedScale"] = (
            float(char_conf.get("speed", 1.0)) + parsed_data.speed_offset
        )
        query["prePhonemeLength"] = parsed_data.pre_pause
        query["postPhonemeLength"] = parsed_data.post_pause

    item = {
        "text": parsed_data.text,
        "voice": {
            "engineId": engine_id,
            "speakerId": speaker_uuid,
            "styleId": style_id,
        },
    }
    if query:
        item["query"] = query

    return audio_key, item


def _build_song_section() -> dict:
    """song セクションのデフォルト構造を生成する"""
    track_key = str(uuid.uuid4())
    return {
        "tpqn": 480,
        "tempos": [{"position": 0, "bpm": 120}],
        "timeSignatures": [{"measureNumber": 1, "beats": 4, "beatType": 4}],
        "tracks": {
            track_key: {
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
        "trackOrder": [track_key],
    }


# ── 公開関数 ──────────────────────────────────────────


def build_vvproj(parsed_items: list[ParsedLine], config: dict) -> dict:
    """ParsedLine のリストから vvproj データ全体を構築する"""
    audio_keys = []
    audio_items = {}

    for item in parsed_items:
        char_conf = config.get(
            item.character, config.get("default", {"style_id": 3, "speed": 1.0})
        )
        key, audio_item = _build_audio_item(item, char_conf)
        audio_keys.append(key)
        audio_items[key] = audio_item

    return {
        "appVersion": APP_VERSION,
        "talk": {
            "audioKeys": audio_keys,
            "audioItems": audio_items,
        },
        "song": _build_song_section(),
    }


def save_vvproj(vvproj_data: dict, output_dir: Path, project_name: str) -> Path:
    """vvproj データを JSON ファイルとして保存する"""
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{project_name}.vvproj"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(vvproj_data, f, ensure_ascii=False, indent=2)

    return file_path
