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
   - 括弧なし                 -> 四国めたん (metan)
   ※ 括弧の対応が正しくない場合（例: 「...」」）はエラーを出力します。

3. ポーズ時間 (間) の指定:
   - フォーマット: [テキスト], [前の間], [後の間]
   - 指定範囲: 0.00 ～ 2.00 (秒)
   - デフォルト値: 0.10
   - カンマが足りない、または値が空の場合はデフォルト値が適用されます。

4. 場面転換:
   - 2行以上の連続空白行がある場合、その直前の台詞の後の間(post_pause)を 0.80 に設定する。

[入力例]
- 「「「こんにちは」」」, 0.5, 1.0  -> 玄野武宏, 前0.5s, 後1.0s
- 「「確かに」」, 0              -> 春日部つむぎ, 前0.0s, 後0.1s(デフォ)
- 「そうなのだ」,, 2.0           -> ずんだもん, 前0.1s(デフォ), 後2.0s
- めたんですわ                  -> 四国めたん, 前0.1s(デフォ), 後0.1s(デフォ)
- （これは読まれません）          -> 無視
"""

import re


def parse_line(line):
    """
    1行のテキストを解析し、構造化された辞書を返す。
    解析不能な場合や無視対象の場合は None を返す。
    """
    line = line.strip()

    # 1. 無視ルールの判定
    if not line:
        return None

    # コメント行の無視
    if (line.startswith("(") and line.endswith(")")) or (
        line.startswith("（") and line.endswith("）")
    ):
        return None

    # 2. カンマで分割 (最大3パーツ)
    parts = [p.strip() for p in line.split(",")]
    raw_text = parts[0]

    # 3. ポーズ時間の解析
    try:
        pre_pause = get_pause_value(parts, 1, 0.10)
        post_pause = get_pause_value(parts, 2, 0.10)
    except ValueError as e:
        raise ValueError(f"パースエラー: {e}")

    # 4. バリデーション
    if not (0.0 <= pre_pause <= 2.0) or not (0.0 <= post_pause <= 2.0):
        raise ValueError(f"ポーズ時間は0.00から2.00の間で指定してください: {line}")

    # 5. キャラクター判定
    char_key, clean_text = identify_character_and_text(raw_text)

    return {
        "type": char_key,
        "text": clean_text,
        "pre_pause": pre_pause,
        "post_pause": post_pause,
    }


def get_pause_value(parts, index, default):
    """
    指定インデックスの値を取り出し、数値に変換する。
    存在しない、または空文字の場合はデフォルト値を返す。
    """
    if len(parts) > index and parts[index] != "":
        try:
            val = float(parts[index])
            return val
        except ValueError:
            raise ValueError(f"値 '{parts[index]}' を数値に変換できません。")
    return default


def identify_character_and_text(text):
    """
    括弧の深さを判定し、対応するキャラクターIDキーと、
    括弧を除去した純粋なテキストを分離して返す。
    """
    # 判定パターンの定義 (深い括弧から順にマッチング)
    patterns = [
        (r"^「「「(.+)」」」$", "takehiro"),
        (r"^「「(.+)」」$", "tsumugi"),
        (r"^「(.+)」$", "zundamon"),
    ]

    for pattern, char_key in patterns:
        match = re.match(pattern, text)
        if match:
            return char_key, match.group(1)

    # 括弧が全くない、あるいは「で始まらない場合
    if not text.startswith("「"):
        return "metan_amaama", text

    # 「 で始まっているが、閉じ括弧が合わない等のケース
    raise ValueError(
        f"括弧の形式が正しくありません (全角「」を使用してください): {text}"
    )


SCENE_BREAK_PAUSE = 0.80


def parse_lines(lines):
    """
    複数行のテキストをまとめて解析し、構造化された辞書のリストを返す。
    2行以上の連続空白行は場面転換とみなし、直前の台詞の post_pause を上書きする。
    """
    parsed_items = []
    blank_count = 0

    for line in lines:
        if not line.strip():
            blank_count += 1
            continue

        result = parse_line(line)

        if result is not None:
            if blank_count >= 2 and parsed_items:
                parsed_items[-1]["post_pause"] = SCENE_BREAK_PAUSE
            parsed_items.append(result)

        blank_count = 0

    return parsed_items
