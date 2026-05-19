import html
import json
import os
import re
import sys
import wave
import math
from fractions import Fraction

# Python 3.11未満の場合は警告を出して終了
try:
    import tomllib
except ImportError:
    print(
        "エラー: このスクリプトは Python 3.11 以降（tomllib標準搭載）で実行してください。"
    )
    sys.exit(1)

BASE_VOICES_DIR = "./voices"
BASE_OUTPUTS_DIR = "./outputs"
GLOBAL_CONFIG_PATH = "./characters.toml"

# 今回のタイムライン設定（1秒＝24フレーム）
FPS = 24.0

# --- スクリプト内デフォルトスタイル（TOMLにキャラ設定がない場合の安全装置） ---
DEFAULT_STYLE = {
    "font": "Al Bayan",
    "fontSize": "80",
    "fontColor": "#ffffff",
    "bold": "1",
    "lineSpacing": "-50",
    "strokeColor": "#000000",
    "strokeSize": 16,
    "position": [0.5, 0.1],
    "shadowColor": "#000000",
    "shadowOffset": [0.0052, -0.0111],
    "shadowBlur": 1,
    "shadowOpacity": 100,
}


def get_wav_duration_frames(file_path):
    with wave.open(file_path, "rb") as w:
        duration_sec = w.getnframes() / w.getframerate()
        return math.ceil(duration_sec * FPS)


def parse_filename(filename):
    match = re.match(r"^(\d+)_(.*?)[(（].*?[)）]_", filename)
    return {"num": match.group(1), "char": match.group(2)} if match else None


def create_gap_object(duration_frames):
    return {
        "OTIO_SCHEMA": "Gap.1",
        "metadata": {},
        "name": "",
        "source_range": {
            "OTIO_SCHEMA": "TimeRange.1",
            "duration": {
                "OTIO_SCHEMA": "RationalTime.1",
                "rate": FPS,
                "value": float(duration_frames),
            },
            "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": FPS, "value": 0.0},
        },
        "effects": [],
        "markers": [],
        "enabled": true,
    }


# PythonのTrue/False/NoneをJSON互換の小文字にするための一時変数
true = True
false = False
null = None


def main():
    project_name = (
        sys.argv[1] if len(sys.argv) > 1 else input("プロジェクト名を入力: ").strip()
    )
    target_project_dir = os.path.join(BASE_VOICES_DIR, project_name)

    if not os.path.exists(target_project_dir):
        print(f"エラー: ディレクトリが見つかりません: {target_project_dir}")
        return

    # TOMLスタイル設定の読み込み
    style_templates = {}
    if os.path.exists(GLOBAL_CONFIG_PATH):
        try:
            with open(GLOBAL_CONFIG_PATH, "rb") as f:
                style_templates = tomllib.load(f).get("styles", {})
        except Exception as e:
            print(
                f"警告: {GLOBAL_CONFIG_PATH} の読み込みに失敗しました。デフォルト設定を使用します。({e})"
            )

    wav_files = sorted(
        [f for f in os.listdir(target_project_dir) if f.endswith(".wav")]
    )
    if not wav_files:
        print(f"エラー: {target_project_dir} 内に .wav ファイルがありません。")
        return

    # 全ファイルの解析とフレーム数の確定
    parsed_clips = []
    unique_chars = []
    total_timeline_frames = 0

    for idx, wav_filename in enumerate(wav_files):
        info = parse_filename(wav_filename)
        if not info:
            continue

        char_name = info["char"]
        if char_name not in unique_chars:
            unique_chars.append(char_name)

        txt_path = os.path.join(
            target_project_dir, os.path.splitext(wav_filename)[0] + ".txt"
        )
        full_text = "（テキストなし）"
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                full_text = f.read().strip()

        wav_path = os.path.join(target_project_dir, wav_filename)
        duration_frames = get_wav_duration_frames(wav_path)

        parsed_clips.append(
            {
                "filename": wav_filename,
                "text": full_text,
                "duration_frames": duration_frames,
                "start_frame": total_timeline_frames,
                "abs_path": os.path.abspath(wav_path),
                "char": char_name,
            }
        )
        total_timeline_frames += duration_frames

    # --- OTIOベース構造の構築 ---
    otio_data = {
        "OTIO_SCHEMA": "Timeline.1",
        "metadata": {"Resolve_OTIO": {"Resolve OTIO Meta Version": "1.0"}},
        "name": project_name,
        "global_start_time": {
            "OTIO_SCHEMA": "RationalTime.1",
            "rate": FPS,
            "value": 86400.0,
        },
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "metadata": {},
            "name": "",
            "source_range": null,
            "effects": [],
            "markers": [],
            "enabled": true,
            "children": [],
        },
    }

    # 1. 字幕用ビデオトラックの初期化
    video_tracks = {}
    for char in unique_chars:
        video_tracks[char] = {
            "OTIO_SCHEMA": "Track.1",
            "metadata": {"Resolve_OTIO": {"Locked": false}},
            "name": f"Subtitle - {char}",
            "source_range": null,
            "effects": [],
            "markers": [],
            "enabled": true,
            "children": [],
            "kind": "Video",
        }

    # 2. 音声用オーディオトラックの初期化
    audio_track_children = []

    # 各クリップを処理してトラックに配置
    for idx, clip in enumerate(parsed_clips):
        style = DEFAULT_STYLE.copy()
        if clip["char"] in style_templates:
            style.update(style_templates[clip["char"]])

        # HTML形式のタイトルブロック生成
        font_weight = "600" if style["bold"] == "1" else "400"
        title_html = (
            f'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n'
            f'<html><head><meta name="qrichtext" content="1" /><style type="text/css">\np, li {{ white-space: pre-wrap; }}\n</style></head>'
            f"<body style=\" font-family:'.AppleSystemUIFont'; font-size:13pt; font-weight:400; font-style:normal;\">\n"
            f'<p align="center" style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; line-height:{style["lineSpacing"]}; -qt-line-height-type: line-distance;">'
            f'<span style=" font-family:\'{style["font"]}\'; font-size:{style["fontSize"]}pt; font-weight:{font_weight}; color:{style["fontColor"]};">{html.escape(clip["text"])}</span></p></body></html>'
        )

        # 字幕クリップオブジェクトの構築
        text_clip = {
            "OTIO_SCHEMA": "Clip.2",
            "metadata": {"Resolve_OTIO": {}},
            "name": "Text",
            "source_range": {
                "OTIO_SCHEMA": "TimeRange.1",
                "duration": {
                    "OTIO_SCHEMA": "RationalTime.1",
                    "rate": FPS,
                    "value": float(clip["duration_frames"]),
                },
                "start_time": {
                    "OTIO_SCHEMA": "RationalTime.1",
                    "rate": FPS,
                    "value": 0.0,
                },
            },
            "effects": [
                {
                    "OTIO_SCHEMA": "Effect.1",
                    "metadata": {
                        "Resolve_OTIO": {
                            "Effect Name": "Transform",
                            "Enabled": true,
                            "Name": "Transform",
                            "Parameters": [],
                            "Type": 2,
                        }
                    },
                    "name": "",
                    "effect_name": "Resolve Effect",
                },
                {
                    "OTIO_SCHEMA": "Effect.1",
                    "metadata": {
                        "Resolve_OTIO": {
                            "Effect Name": "Cropping",
                            "Enabled": true,
                            "Name": "Cropping",
                            "Parameters": [],
                            "Type": 3,
                        }
                    },
                    "name": "",
                    "effect_name": "Resolve Effect",
                },
                {
                    "OTIO_SCHEMA": "Effect.1",
                    "metadata": {
                        "Resolve_OTIO": {
                            "Effect Name": "Composite",
                            "Enabled": true,
                            "Name": "Composite",
                            "Parameters": [],
                            "Type": 1,
                        }
                    },
                    "name": "",
                    "effect_name": "Resolve Effect",
                },
                {
                    "OTIO_SCHEMA": "Effect.1",
                    "metadata": {
                        "Resolve_OTIO": {
                            "Effect Name": "Video Faders",
                            "Enabled": true,
                            "Name": "Video Faders",
                            "Parameters": [],
                            "Type": 36,
                        }
                    },
                    "name": "",
                    "effect_name": "Resolve Effect",
                },
            ],
            "markers": [],
            "enabled": true,
            "media_references": {
                "DEFAULT_MEDIA": {
                    "OTIO_SCHEMA": "GeneratorReference.1",
                    "metadata": {"Resolve_OTIO": {"Generator Type": "Rich"}},
                    "name": "Text",
                    "available_range": null,
                    "available_image_bounds": null,
                    "generator_kind": "Rich",
                    "parameters": {
                        "Resolve_OTIO": [
                            {
                                "Effect Name": "Rich Text",
                                "Enabled": true,
                                "Name": "Rich Text",
                                "Parameters": [
                                    {
                                        "Default Parameter Value": "Title",
                                        "Parameter ID": "rich text",
                                        "Parameter Value": "Title",
                                        "Variant Type": "String",
                                    },
                                    {
                                        "Parameter ID": "title blob",
                                        "Title HTML": title_html,
                                    },
                                    {
                                        "Default Parameter Value": 4,
                                        "Parameter ID": "anchor",
                                        "Parameter Value": 4,
                                        "Variant Type": "UInt",
                                    },
                                    {
                                        "Default Parameter Value": [0.5, 0.5],
                                        "Key Frames": {},
                                        "Parameter ID": "position",
                                        "Parameter Value": style["position"],
                                        "Variant Type": "POINTF",
                                    },
                                    {
                                        "Default Parameter Value": 1.0,
                                        "Key Frames": {},
                                        "Parameter ID": "transformationZoomX",
                                        "Parameter Value": 1.0,
                                        "Variant Type": "Double",
                                        "maxValue": 4.0,
                                        "minValue": 0.25,
                                    },
                                    {
                                        "Default Parameter Value": 1.0,
                                        "Key Frames": {},
                                        "Parameter ID": "transformationZoomY",
                                        "Parameter Value": 1.0,
                                        "Variant Type": "Double",
                                        "maxValue": 4.0,
                                        "minValue": 0.25,
                                    },
                                    {
                                        "Default Parameter Value": true,
                                        "Parameter ID": "transformationZoomLink",
                                        "Parameter Value": true,
                                        "Variant Type": "Bool",
                                    },
                                    {
                                        "Default Parameter Value": 0.0,
                                        "Key Frames": {},
                                        "Parameter ID": "transformationRotationAngle",
                                        "Parameter Value": 0.0,
                                        "Variant Type": "Double",
                                        "maxValue": 100000.0,
                                        "minValue": -100000.0,
                                    },
                                ],
                                "Type": 24,
                            },
                            {
                                "Effect Name": "Drop Shadow",
                                "Enabled": true,
                                "Name": "Drop Shadow",
                                "Parameters": [
                                    {
                                        "Default Parameter Value": "#000000",
                                        "Parameter ID": "shadow color",
                                        "Parameter Value": style["shadowColor"],
                                        "Variant Type": "Color",
                                    },
                                    {
                                        "Default Parameter Value": [0.0, 0.0],
                                        "Key Frames": {},
                                        "Parameter ID": "shadow offset",
                                        "Parameter Value": style["shadowOffset"],
                                        "Variant Type": "POINTF",
                                    },
                                    {
                                        "Default Parameter Value": 20,
                                        "Key Frames": {},
                                        "Parameter ID": "shadow",
                                        "Parameter Value": style["shadowBlur"],
                                        "Variant Type": "Int",
                                        "maxValue": 100.0,
                                        "minValue": 1.0,
                                    },
                                    {
                                        "Default Parameter Value": 75,
                                        "Key Frames": {},
                                        "Parameter ID": "shadow opacity",
                                        "Parameter Value": style["shadowOpacity"],
                                        "Variant Type": "Int",
                                        "maxValue": 100.0,
                                        "minValue": 0.0,
                                    },
                                ],
                                "Type": 8,
                            },
                            {
                                "Effect Name": "Stroke",
                                "Enabled": true,
                                "Name": "Stroke",
                                "Parameters": [
                                    {
                                        "Default Parameter Value": "#ffffff",
                                        "Parameter ID": "strokeColor",
                                        "Parameter Value": style["strokeColor"],
                                        "Variant Type": "Color",
                                    },
                                    {
                                        "Default Parameter Value": 1,
                                        "Parameter ID": "strokeSize",
                                        "Parameter Value": style["strokeSize"],
                                        "Variant Type": "Int",
                                        "maxValue": 16.0,
                                        "minValue": 0.0,
                                    },
                                    {
                                        "Default Parameter Value": false,
                                        "Parameter ID": "strokeOutsideOnly",
                                        "Parameter Value": true,
                                        "Variant Type": "Bool",
                                    },
                                ],
                                "Type": 28,
                            },
                        ]
                    },
                }
            },
            "active_media_reference_key": "DEFAULT_MEDIA",
        }

        # 各ビデオトラックへの振り分け
        for char in unique_chars:
            if char == clip["char"]:
                video_tracks[char]["children"].append(text_clip)
            else:
                video_tracks[char]["children"].append(
                    create_gap_object(clip["duration_frames"])
                )

        # オーディオクリップの構築
        audio_clip = {
            "OTIO_SCHEMA": "Clip.2",
            "metadata": {"Resolve_OTIO": {}},
            "name": clip["filename"],
            "source_range": {
                "OTIO_SCHEMA": "TimeRange.1",
                "duration": {
                    "OTIO_SCHEMA": "RationalTime.1",
                    "rate": FPS,
                    "value": float(clip["duration_frames"]),
                },
                "start_time": {
                    "OTIO_SCHEMA": "RationalTime.1",
                    "rate": FPS,
                    "value": 0.0,
                },
            },
            "effects": [],
            "markers": [],
            "enabled": true,
            "media_references": {
                "DEFAULT_MEDIA": {
                    "OTIO_SCHEMA": "ExternalReference.1",
                    "metadata": {},
                    "name": clip["filename"],
                    "available_range": {
                        "OTIO_SCHEMA": "TimeRange.1",
                        "duration": {
                            "OTIO_SCHEMA": "RationalTime.1",
                            "rate": FPS,
                            "value": float(
                                clip["clip_duration_frames"]
                                if "clip_duration_frames" in clip
                                else clip["duration_frames"]
                            ),
                        },
                        "start_time": {
                            "OTIO_SCHEMA": "RationalTime.1",
                            "rate": FPS,
                            "value": 0.0,
                        },
                    },
                    "available_image_bounds": null,
                    "target_url": clip["abs_path"],
                }
            },
            "active_media_reference_key": "DEFAULT_MEDIA",
        }
        audio_track_children.append(audio_clip)

    # 【修正箇所】最背面に空の背景用V1トラックを1本挿入する
    bg_track = {
        "OTIO_SCHEMA": "Track.1",
        "metadata": {"Resolve_OTIO": {"Locked": false}},
        "name": "Background",
        "source_range": null,
        "effects": [],
        "markers": [],
        "enabled": true,
        "children": [create_gap_object(total_timeline_frames)],
        "kind": "Video",
    }
    otio_data["tracks"]["children"].append(bg_track)

    # タイムラインに全字幕トラックを結合 (V2, V3, V4... と順に積まれる)
    for char in unique_chars:
        otio_data["tracks"]["children"].append(video_tracks[char])

    # オーディオトラックを追加
    audio_track = {
        "OTIO_SCHEMA": "Track.1",
        "metadata": {
            "Resolve_OTIO": {"Audio Type": "Mono", "Locked": false, "SoloOn": false}
        },
        "name": "Audio 1",
        "source_range": null,
        "effects": [],
        "markers": [],
        "enabled": true,
        "children": audio_track_children,
        "kind": "Audio",
    }
    otio_data["tracks"]["children"].append(audio_track)

    # 出力
    os.makedirs(BASE_OUTPUTS_DIR, exist_ok=True)
    output_file_path = os.path.join(BASE_OUTPUTS_DIR, f"{project_name}.otio")

    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(otio_data, f, indent=4, ensure_ascii=False)

    print(f"\n[成功] .otio 生成に成功しました -> {output_file_path}")


if __name__ == "__main__":
    main()
