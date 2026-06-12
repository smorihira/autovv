"""voicevox-parser: テキスト台本から VOICEVOX プロジェクトを生成する"""

import json
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
from src.parse_input import build_metadata, parse_lines
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

    project_name = (
        sys.argv[1] if len(sys.argv) > 1 else input("プロジェクト名を入力してください: ").strip()
    ) or "untitled"

    plots_dir = _ROOT.parent / "plots"
    search_dirs = [plots_dir, plots_dir / "ai_plots"]
    plot_file = next(
        (d / f"{project_name}.txt" for d in search_dirs if (d / f"{project_name}.txt").exists()),
        None,
    )
    if plot_file is None:
        searched = ", ".join(str(d / f"{project_name}.txt") for d in search_dirs)
        print(f"エラー: 台本が見つかりません。検索場所: {searched}")
        return

    print(f"{plot_file.name} を読み込み中...")
    engine_proc = ensure_engine()

    lines = plot_file.read_text(encoding="utf-8").splitlines()
    parsed_items = parse_lines(lines)

    if not parsed_items:
        print("データがないため終了します。")
        return

    vvproj_data = build_vvproj(parsed_items, config)
    file_path = save_vvproj(vvproj_data, output_dir, project_name)
    print(f"プロジェクトを作成しました: {file_path}")

    # resolve-exporter 用の voices ディレクトリを作成
    voices_dir = _ROOT.parent / "voices" / project_name
    voices_dir.mkdir(parents=True, exist_ok=True)
    print(f"voices ディレクトリを作成しました: {voices_dir}")

    # resolve-exporter 用のメタデータを出力
    metadata_path = voices_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(build_metadata(parsed_items), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"メタデータを出力しました: {metadata_path}")

    restart_with_project(file_path, engine_proc)


if __name__ == "__main__":
    main()
