"""
VOICEVOX 入力テキスト解析モジュール (vv-bridge)

[基本仕様]
1. 無視ルール:
   - 空行、またはスペースのみの行は無視されます。
   - 丸括弧（半角 '()' または全角 '（）'）で囲まれた行はコメントと見なし無視されます。

2. キャラクター判定 (括弧の重なり優先順位):
   - 三重括弧 「「「...」」」 -> 玄野武宏 (takehiro)
   - 二重括弧 「「...」」     -> 春日部つむぎ (tsumugi)
   - 一重括弧 「...」         -> ずんだもん (zundamon)
   - 括弧なし                 -> 四国めたん (metan_amaama)
   ※ 括弧の対応が正しくない場合（例: 「...」」）はエラーを出力します。

3. ポーズ時間 (間) の指定:
   - フォーマット: [テキスト], [前の間], [後の間]
   - 指定範囲: 0.00 ～ 2.00 (秒)
   - デフォルト値: 0.10
   - カンマが足りない、または値が空の場合はデフォルト値が適用されます。
   - 括弧「」内のカンマはテキストの一部として扱われます。

4. 場面転換:
   - 2行以上の連続空白行がある場合、その直前の台詞の後の間(post_pause)を 0.80 に設定する。

[入力例]
- 「「「こんにちは」」」, 0.5, 1.0  -> 玄野武宏, 前0.5s, 後1.0s
- 「「確かに」」, 0              -> 春日部つむぎ, 前0.0s, 後0.1s(デフォ)
- 「そうなのだ」,, 2.0           -> ずんだもん, 前0.1s(デフォ), 後2.0s
- めたんですわ                  -> 四国めたん, 前0.1s(デフォ), 後0.1s(デフォ)
- （これは読まれません）          -> 無視
"""

from dataclasses import dataclass

# ── 定数 ──────────────────────────────────────────────

PAUSE_DEFAULT = 0.10
PAUSE_MIN = 0.00
PAUSE_MAX = 2.00
SCENE_BREAK_PAUSE = 0.80

# キャラクター定義: (開き括弧, 閉じ括弧, キー名)
# 深い括弧から順に判定する
CHARACTER_BRACKETS = [
    ("「「「", "」」」", "takehiro"),
    ("「「", "」」", "tsumugi"),
    ("「", "」", "zundamon"),
]
DEFAULT_CHARACTER = "metan_amaama"

# コメント行の括弧ペア
COMMENT_BRACKETS = [("(", ")"), ("（", "）")]


# ── データ構造 ────────────────────────────────────────


@dataclass
class ParsedLine:
    """解析済みの1行を表す構造体"""

    character: str
    text: str
    pre_pause: float
    post_pause: float


# ── 内部関数 ──────────────────────────────────────────


def _is_comment(line: str) -> bool:
    """コメント行かどうかを判定する"""
    return any(
        line.startswith(open_b) and line.endswith(close_b)
        for open_b, close_b in COMMENT_BRACKETS
    )


def _split_text_and_pauses(line: str) -> tuple[str, list[str]]:
    """
    テキスト部分とポーズ値部分を分離する。
    括弧「」内のカンマはテキストの一部として扱う。
    """
    last_bracket = line.rfind("」")
    if last_bracket != -1:
        text_part = line[: last_bracket + 1]
        remainder = line[last_bracket + 1 :]
        parts = [p.strip() for p in remainder.split(",")]
        return text_part, parts[1:]  # 最初の空要素をスキップ

    # 括弧なし: 通常のカンマ分割
    parts = [p.strip() for p in line.split(",")]
    return parts[0], parts[1:]


def _parse_pause(value: str, default: float = PAUSE_DEFAULT) -> float:
    """ポーズ値を解析する。空文字の場合はデフォルト値を返す。"""
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"値 '{value}' を数値に変換できません。")


def _identify_character(text: str) -> tuple[str, str]:
    """
    括弧の深さからキャラクターを判定し、
    (キャラクターキー, 括弧を除去したテキスト) を返す。
    """
    for open_b, close_b, char_key in CHARACTER_BRACKETS:
        if text.startswith(open_b) and text.endswith(close_b):
            inner = text[len(open_b) : -len(close_b)]
            return char_key, inner

    if not text.startswith("「"):
        return DEFAULT_CHARACTER, text

    raise ValueError(
        f"括弧の形式が正しくありません (全角「」を使用してください): {text}"
    )


# ── 公開関数 ──────────────────────────────────────────


def parse_line(line: str) -> ParsedLine | None:
    """
    1行のテキストを解析し、ParsedLine を返す。
    無視対象の行は None を返す。
    """
    line = line.strip()
    if not line or _is_comment(line):
        return None

    text_part, pause_parts = _split_text_and_pauses(line)

    pre_pause = _parse_pause(pause_parts[0] if len(pause_parts) > 0 else "")
    post_pause = _parse_pause(pause_parts[1] if len(pause_parts) > 1 else "")

    if not (PAUSE_MIN <= pre_pause <= PAUSE_MAX) or not (
        PAUSE_MIN <= post_pause <= PAUSE_MAX
    ):
        raise ValueError(
            f"ポーズ時間は{PAUSE_MIN:.2f}から{PAUSE_MAX:.2f}の間で指定してください: {line}"
        )

    character, clean_text = _identify_character(text_part)

    return ParsedLine(
        character=character,
        text=clean_text,
        pre_pause=pre_pause,
        post_pause=post_pause,
    )


def parse_lines(lines: list[str]) -> list[ParsedLine]:
    """
    複数行のテキストをまとめて解析し、ParsedLine のリストを返す。
    2行以上の連続空白行は場面転換とみなし、直前の台詞の post_pause を上書きする。
    パースエラーは行番号付きで報告し、該当行をスキップして処理を続行する。
    """
    parsed_items: list[ParsedLine] = []
    blank_count = 0

    for line_num, line in enumerate(lines, 1):
        if not line.strip():
            blank_count += 1
            continue

        try:
            result = parse_line(line)
        except ValueError as e:
            print(f"行{line_num}: {e}")
            blank_count = 0
            continue

        if result is not None:
            if blank_count >= 2 and parsed_items:
                parsed_items[-1].post_pause = SCENE_BREAK_PAUSE
            parsed_items.append(result)

        blank_count = 0

    return parsed_items
