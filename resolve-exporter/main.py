"""DaVinci Resolve 用 OTIO タイムライン生成スクリプト

VOICEVOX で生成した WAV ファイルと対応するテキストファイルから、
DaVinci Resolve にインポート可能な .otio ファイルを生成する。
"""

import json
import os
import sys

try:
    import tomllib
except ImportError:
    print("エラー: このスクリプトは Python 3.11 以降で実行してください。")
    sys.exit(1)

from otio_builder import build_timeline
from scan_project import scan_project

# ── 定数 ──────────────────────────────────────────────

_ROOT = os.path.dirname(os.path.abspath(__file__))
VOICES_DIR = os.path.join(_ROOT, "voices")
OUTPUTS_DIR = os.path.join(_ROOT, "outputs")
CONFIG_PATH = os.path.join(_ROOT, "characters.toml")


# ── 設定読み込み ──────────────────────────────────────


def _load_style_config():
    """characters.toml からスタイル設定を読み込む"""
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f).get("styles", {})
    except Exception as e:
        print(f"警告: {CONFIG_PATH} の読み込みに失敗しました。({e})")
        return {}


# ── メイン ────────────────────────────────────────────


def main():
    project_name = (
        sys.argv[1] if len(sys.argv) > 1 else input("プロジェクト名を入力: ").strip()
    )
    project_dir = os.path.join(VOICES_DIR, project_name)

    if not os.path.exists(project_dir):
        print(f"エラー: ディレクトリが見つかりません: {project_dir}")
        return

    style_templates = _load_style_config()
    clips, chars, total_frames = scan_project(project_dir)

    if not clips:
        print(f"エラー: {project_dir} 内に .wav ファイルがありません。")
        return

    timeline = build_timeline(project_name, clips, chars, total_frames, style_templates)

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUTS_DIR, f"{project_name}.otio")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=4, ensure_ascii=False)

    print(f"\n[成功] .otio 生成に成功しました -> {output_path}")


if __name__ == "__main__":
    main()
