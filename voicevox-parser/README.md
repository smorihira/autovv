# voicevox-parser

テキストの台本（`plot.txt`）から VOICEVOX プロジェクトファイル（`.vvproj`）を自動生成するツール。  

## 必要環境

- Python 3.11 以上（3.11 未満の場合は `pip install toml` が必要）
- macOS（VOICEVOX の起動制御に `osascript` / `open` を使用）
- [VOICEVOX](https://voicevox.hiroshiba.jp/) がインストール済みであること（`/Applications/VOICEVOX.app`）

## セットアップ

```bash
cd voicevox-parser
```

`.env` ファイルを作成し、生成される `.vvproj` の出力先ディレクトリを設定してください。

```
VVPROJ_OUTPUT_DIR=/path/to/your/output/dir
```

外部ライブラリは不要です（標準ライブラリのみ使用）。

## 使い方

1. `plot.txt` に台本を記述する
2. `python3 main.py` を実行
3. プロジェクト名を入力（ファイル名になる）
4. `.vvproj` が生成され、VOICEVOX で自動的に開かれる

### 実行時の動作

```
$ python3 main.py
plot.txt を読み込み中...
VOICEVOXエンジンが見つかりません。エンジンを起動します...
VOICEVOXエンジンが起動しました。
プロジェクト名を入力してください: my_project
プロジェクトを作成しました: /path/to/output/my_project.vvproj
```

- VOICEVOX エンジンが未起動の場合、GUI を開かずにエンジンだけバックグラウンドで起動します
- 各台詞について VOICEVOX API（`POST /audio_query`）を呼び出し、アクセント句データを取得します
- VOICEVOX が既に開いている場合は一度終了し（保存ダイアログにも対応）、新しいプロジェクトで開き直します
- スクリプトが起動したエンジンは、GUI で開く際に自動停止します（GUI が内蔵エンジンを使用するため）

## plot.txt の書き方

### キャラクター指定

括弧の深さでキャラクターを判別します。

| 書き方 | キャラクター |
|---|---|
| テキスト（括弧なし） | 四国めたん（あまあま） |
| `「テキスト」` | ずんだもん |
| `「「テキスト」」` | 春日部つむぎ |
| `「「「テキスト」」」` | 玄野武宏 |

キャラクターと `style_id` の対応は `characters.toml` で変更できます。

### ポーズ時間（間）

カンマ区切りで前後の間を指定できます（0.00〜2.00 秒、デフォルト 0.10）。

```
テキスト, 前の間, 後の間
```

| 記法 | 前の間 | 後の間 |
|---|---|---|
| `「こんにちは」, 0.5, 1.0` | 0.5s | 1.0s |
| `「「そうだね」」, 0` | 0.0s | 0.1s（デフォルト） |
| `やあ,, 2.0` | 0.1s（デフォルト） | 2.0s |
| `ただいま` | 0.1s（デフォルト） | 0.1s（デフォルト） |

### コメント

丸括弧（全角・半角どちらでも可）で囲むとコメント扱いになり、読み上げされません。

```
（これはコメントです）
(This is also a comment)
```

### 場面転換

2行以上の連続空白行を入れると**場面転換**とみなし、直前の台詞の後の間を **0.80 秒**に自動設定します。  
1行だけの空白行は単に無視されます。

```
「前のシーンの最後の台詞」
                              ← 空白行1
                              ← 空白行2（2行以上で場面転換）
「次のシーンの最初の台詞」
```

### plot.txt の例

```
「今日はいい天気なのだ」
そうねえ, 0, 0
「「散歩でも行こうよー」」


（ここから本題）

「「「速報です」」」, 0.5, 0.5
なんのニュースよ
```

この例では「散歩でも行こうよー」の後に空白行が2行あるため、この台詞の後の間が 0.80 秒になります。

## ファイル構成

```
voicevox-parser/
├── main.py            # メイン処理（API呼び出し、vvproj生成、VOICEVOX起動）
├── parse_input.py     # 入力テキストの解析ロジック
├── characters.toml    # キャラクターごとの style_id・速度設定
├── plot.txt           # 入力台本（ここに台本を書く）
├── .env               # 出力先ディレクトリの設定
└── README.md
```

## characters.toml

キャラクターの音声スタイルと速度を設定します。以下は設定例です（`style_id` や `speed` は好みに合わせて変更してください）。

```toml
[metan_amaama]
style_id = 0
speed = 1.35

[zundamon]
style_id = 3
speed = 1.42

[tsumugi]
style_id = 8
speed = 1.30

[takehiro]
style_id = 11
speed = 1.30
```

キーの名前（`metan_amaama`, `zundamon` 等）は `parse_input.py` のキャラクター判定と対応しています。  
`style_id` は VOICEVOX のスタイル ID です。VOICEVOX エディタの「設定」や API（`GET /speakers`）で確認できます。

## 注意事項

- VOICEVOX のインストールパスが `/Applications/VOICEVOX.app` 以外の場合は `main.py` のパスを修正してください
- VOICEVOX エンジンの API はデフォルトで `http://localhost:50021` を使用します
- 生成される `.vvproj` の `appVersion` は `0.24.0` に設定されています
