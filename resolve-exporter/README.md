# resolve-exporter

VOICEVOX で生成した WAV ファイルと対応するテキストファイルから、DaVinci Resolve にインポート可能な OTIO タイムラインファイル（`.otio`）を自動生成するツール。

## 必要環境

- Python 3.11 以上（標準ライブラリの `tomllib` を使用）
- 外部ライブラリ不要

## 使い方

### 1. 入力ファイルを配置

`voices/<プロジェクト名>/` ディレクトリに、WAV ファイルと同名の `.txt` ファイルをペアで配置する。

```
voices/my_project/
  001_ずんだもん（ノーマル）_こんにちは.wav
  001_ずんだもん（ノーマル）_こんにちは.txt
  002_四国めたん（あまあま）_やっほー.wav
  002_四国めたん（あまあま）_やっほー.txt
  ...
```

ファイル名の形式: `<連番>_<キャラクター名>（<スタイル>）_<セリフ冒頭>.<拡張子>`

### 2. 実行

```bash
python3 main.py <プロジェクト名>
```

引数を省略するとプロジェクト名の入力を求められる。

### 3. 出力

`outputs/<プロジェクト名>.otio` が生成される。DaVinci Resolve の「メディアプールにタイムラインを読み込む」でインポートできる。

## 生成されるタイムラインの構造

| トラック | 種類 | 内容 |
|---|---|---|
| V1 | Video | Background（空の Gap、全体の長さ） |
| V2〜 | Video | キャラクターごとの字幕トラック（`Subtitle - <キャラクター名>`） |
| A1 | Audio | 全 WAV を連結したオーディオトラック |

字幕はキャラクターごとに独立したトラックに配置されるため、Resolve 上でキャラクター単位の一括編集が可能。

## 字幕スタイルの設定

`characters.toml` でキャラクターごとの字幕スタイルを定義する。

```toml
[styles."ずんだもん"]
font = "Al Bayan"
fontSize = "80"
fontColor = "#ffffff"
bold = "1"
lineSpacing = "-50"
strokeColor = "#000000"
strokeSize = 16
position = [0.5, 0.1]
shadowColor = "#7c9849"
shadowOffset = [0.0052, -0.0111]
shadowBlur = 1
shadowOpacity = 100
```

設定がないキャラクターにはデフォルトスタイル（白文字・黒縁取り・黒影）が適用される。

### パラメータ一覧

| パラメータ | 型 | 説明 |
|---|---|---|
| `font` | string | フォント名 |
| `fontSize` | string | フォントサイズ (pt) |
| `fontColor` | string | 文字色 (HEX) |
| `bold` | string | `"1"` で太字 |
| `lineSpacing` | string | 行間調整（負の値で詰まる） |
| `strokeColor` | string | 縁取りの色 (HEX) |
| `strokeSize` | int | 縁取りの太さ (0〜16) |
| `position` | [float, float] | 配置位置 [X, Y]（0.5 で中央、Y=0.1 で下部字幕） |
| `shadowColor` | string | 影の色 (HEX) |
| `shadowOffset` | [float, float] | 影のオフセット [X, Y] |
| `shadowBlur` | int | 影のボケ (1 でクッキリ) |
| `shadowOpacity` | int | 影の不透明度 (0〜100) |

## ファイル構成

```
resolve-exporter/
  main.py           # オーケストレーション（設定読み込み → 走査 → 構築 → 出力）
  scan_project.py   # WAV ファイル走査・ファイル名解析・テキスト読み込み
  otio_builder.py   # OTIO クリップ・タイムライン構築
  characters.toml   # キャラクター別字幕スタイル設定
  voices/           # 入力ディレクトリ（WAV + TXT）
  outputs/          # 出力ディレクトリ（.otio）
```

## 既知の制限

### Stroke（縁取り）が OTIO インポート時に無視される

DaVinci Resolve は OTIO エクスポート時に Stroke メタデータを正しく出力するが、**インポート時には Stroke パラメータ（`strokeSize`, `strokeColor`, `strokeOutsideOnly`）を完全に無視する**。そのため、本ツールで生成した `.otio` をインポートしても縁取りが反映されない。

インポート後に Resolve 上で手動設定するか、Fusion タイトルで代替する必要がある。

Blackmagic Design のフォーラムへ Feature Request を投稿済み:

> **FR: Support "Stroke" metadata when importing OpenTimelineIO (.otio)**
>
> Currently, DaVinci Resolve does not read "Stroke" (Border) effects when importing an OTIO timeline, even though it exports them correctly. All stroke parameters (strokeSize, strokeColor, strokeOutsideOnly) are completely ignored during import.
>
> Please fix the OTIO importer to support "Stroke" metadata so that we can perfectly round-trip text styles between external tools and Resolve.
