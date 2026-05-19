"""voicevox-parser: テキスト台本から VOICEVOX プロジェクトを生成する"""

import os
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import toml as tomllib
    except ImportError:
        print("エラー: Python 3.11未満の環境では `pip install toml` が必要です。")
        sys.exit(1)

from pathlib import Path

from src.app_control import restart_with_project
from src.parse_input import parse_lines
from src.voicevox_api import ensure_engine
from src.vvproj_builder import build_vvproj, save_vvproj

# ── 設定 ──────────────────────────────────────────────

_ROOT = Path(__file__).parent


def _load_env() -> None:
    """同階層の .env から環境変数を読み込む"""
    env_path = _ROOT / "config" / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _load_config() -> dict:
    """characters.toml を読み込む"""
    config_path = _ROOT / "config" / "characters.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    return {}


# ── メイン ────────────────────────────────────────────


def main():
    _load_env()
    config = _load_config()
    output_dir = Path(os.environ.get("VVPROJ_OUTPUT_DIR", "output")).expanduser()

    plot_file = _ROOT / "plot.txt"
    if not plot_file.exists():
        print("エラー: plot.txt が見つかりません。")
        return

    print("plot.txt を読み込み中...")
    engine_proc = ensure_engine()

    lines = plot_file.read_text(encoding="utf-8").splitlines()
    parsed_items = parse_lines(lines)

    if not parsed_items:
        print("データがないため終了します。")
        return

    project_name = input("プロジェクト名を入力してください: ").strip() or "untitled"

    vvproj_data = build_vvproj(parsed_items, config)
    file_path = save_vvproj(vvproj_data, output_dir, project_name)
    print(f"プロジェクトを作成しました: {file_path}")

    # resolve-exporter 用の voices ディレクトリを作成
    voices_dir = _ROOT.parent / "voices" / project_name
    voices_dir.mkdir(parents=True, exist_ok=True)
    print(f"voices ディレクトリを作成しました: {voices_dir}")

    restart_with_project(file_path, engine_proc)


if __name__ == "__main__":
    main()
