"""プロジェクトディレクトリの WAV ファイル走査・解析"""

import math
import os
import re
import wave

FPS = 24.0


def _get_wav_duration_frames(file_path):
    with wave.open(file_path, "rb") as w:
        return math.ceil(w.getnframes() / w.getframerate() * FPS)


def _parse_filename(filename):
    match = re.match(r"^(\d+)_(.*?)[(（].*?[)）]_", filename)
    return {"num": match.group(1), "char": match.group(2)} if match else None


def scan_project(project_dir):
    """
    WAV ファイルを解析し、
    (クリップ情報リスト, ユニークキャラクターリスト, 総フレーム数) を返す。
    """
    wav_files = sorted(f for f in os.listdir(project_dir) if f.endswith(".wav"))
    if not wav_files:
        return [], [], 0

    clips = []
    chars = []
    total_frames = 0

    for wav_filename in wav_files:
        info = _parse_filename(wav_filename)
        if not info:
            continue

        if info["char"] not in chars:
            chars.append(info["char"])

        txt_path = os.path.join(project_dir, os.path.splitext(wav_filename)[0] + ".txt")
        text = "（テキストなし）"
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read().strip()

        wav_path = os.path.join(project_dir, wav_filename)
        duration = _get_wav_duration_frames(wav_path)

        clips.append(
            {
                "filename": wav_filename,
                "text": text,
                "duration_frames": duration,
                "start_frame": total_frames,
                "abs_path": os.path.abspath(wav_path),
                "char": info["char"],
            }
        )
        total_frames += duration

    return clips, chars, total_frames
