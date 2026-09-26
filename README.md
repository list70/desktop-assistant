# 🤖 ローカルAI デスクトップアシスタント

デスクトップ上に常駐する、完全ローカルで動作するAIアシスタントです。

![Desktop Assistant](https://img.shields.io/badge/Platform-Windows-blue)
![Python](https://img.shields.io/badge/Python-3.10--3.12-green)
![Electron](https://img.shields.io/badge/Electron-33+-purple)

## ✨ 機能

- 🎤 **音声入力**: マイクで話しかけて対話（faster-whisper）
- 💬 **テキスト入力**: チャット形式でテキスト入力
- 🔊 **音声出力**: アシスタントが声で返答（Kokoro-82M）
- 🧍 **3D/2Dキャラクター**: VRMモデルを読み込んで好きなキャラを表示
- 🧠 **ローカルLLM**: Ollamaでインストール済みのモデルを選んでローカル推論
- 🛠️ **エージェント機能**: ファイル操作、Web検索、アプリ起動等を自動実行
- 🎭 **感情表現**: 応答に応じてキャラクターの表情が変化
- 👄 **リップシンク**: 音声出力に合わせて口が動く

## 🏗️ アーキテクチャ

```
┌─────────────────────────────────┐
│    Electron (フロントエンド)      │
│  ┌──────────┐  ┌──────────────┐ │
│  │ Three.js │  │   チャットUI   │ │
│  │ VRMキャラ │  │  テキスト入力  │ │
│  └──────────┘  │  マイクボタン  │ │
│                └──────────────┘ │
│         WebSocket 通信           │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│    Python (バックエンド)          │
│  ┌──────┐ ┌─────┐ ┌──────────┐ │
│  │ STT  │ │ LLM │ │  Agent   │ │
│  │Whisper│ │Ollama│ │smolagents│ │
│  └──────┘ └─────┘ └──────────┘ │
│  ┌──────┐ ┌─────────────────┐  │
│  │ TTS  │ │    ツール群      │  │
│  │Kokoro│ │ファイル/Web/Sys  │  │
│  └──────┘ └─────────────────┘  │
└─────────────────────────────────┘
```

## 📋 必要環境

| 項目 | 要件 |
|:---|:---|
| OS | Windows 10/11 |
| Python | 3.10 - 3.12 |
| Node.js | 18+ |
| RAM | 16GB 以上推奨 |
| GPU | NVIDIA GPU 推奨（なくても動作可） |
| ストレージ | 約10GB（モデル含む） |

## 🚀 セットアップ

### 1. 前提ソフトウェアのインストール

- [Python 3.10-3.12](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [Ollama](https://ollama.com/download/windows)
- [espeak-ng](https://github.com/espeak-ng/espeak-ng/releases)（TTS用）

### 2. セットアップスクリプトの実行

```powershell
cd desktop-assistant
.\scripts\setup.ps1
```

このスクリプトが以下を実行します:
- Python仮想環境の作成
- Pythonパッケージのインストール
- Node.jsパッケージのインストール
- Ollamaのインストール済みモデル確認（モデル自体は自動ダウンロードしません）

モデルがまだない場合は、Ollamaを起動して `ollama pull qwen2.5:7b` などで取得してください。アプリ右上の歯車から、ダウンロード済みモデルを選べます。

### 3. 起動

```powershell
.\scripts\start.ps1
```

## 🎮 使い方

### テキスト入力
1. チャット欄にテキストを入力
2. Enterキーまたは送信ボタンをクリック
3. アシスタントが返答（テキスト + 音声）

### 音声入力
1. 🎤 マイクボタンをクリック（または Spaceキー長押し）
2. 話しかける
3. もう一度クリックで送信（Spaceキーを離す）
4. 音声が文字起こしされ、アシスタントが返答

### キャラクター変更
`electron/assets/models/aura.vrm` を置き換えてからアプリを再起動してください。歯車の設定画面ではOllamaモデルを切り替えられます。

### ショートカットキー
| キー | 動作 |
|:---|:---|
| `Ctrl+Shift+A` | ウィンドウの表示/非表示 |
| `Space` (長押し) | プッシュ・トゥ・トーク |
| `Enter` | メッセージ送信 |
| `Escape` | 設定パネルを閉じる |

## 🛠️ エージェント機能

アシスタントは以下のツールを自律的に使用できます:

| ツール | 説明 | 使用例 |
|:---|:---|:---|
| ファイル読み取り | ファイルの内容を読む | 「このファイルの中身を教えて」 |
| ファイル書き込み | ファイルにテキストを書く | 「メモを作成して」 |
| ディレクトリ一覧 | フォルダの中身を表示 | 「デスクトップにあるファイルは？」 |
| Web検索 | インターネットで検索 | 「最新のニュースを調べて」 |
| 現在時刻 | 日時を取得 | 「今何時？」 |
| アプリ起動 | アプリケーションを開く | 「メモ帳を開いて」 |

## ⚙️ 設定

環境変数で各種設定を変更できます:

```powershell
# LLMモデルの変更
$env:LLM_MODEL = "qwen3:14b"

# Whisperモデルサイズの変更
$env:WHISPER_MODEL_SIZE = "medium"

# TTSの声の変更
$env:TTS_VOICE = "jf_alpha"
```

## 📁 プロジェクト構成

```
desktop-assistant/
├── electron/              # Electron フロントエンド
│   ├── main.js            # メインプロセス
│   ├── preload.js         # セキュアIPC
│   ├── renderer/          # レンダラー
│   │   ├── index.html     # メインUI
│   │   ├── styles.css     # スタイル
│   │   ├── app.js         # アプリロジック
│   │   ├── character.js   # キャラクター制御
│   │   ├── chat.js        # チャットUI
│   │   ├── voice-input.js # 音声入力
│   │   └── voice-output.js# 音声出力
│   └── assets/models/     # VRMモデル配置
│
├── backend/               # Python バックエンド
│   ├── main.py            # FastAPIサーバー
│   ├── config.py          # 設定
│   ├── stt/               # 音声認識
│   ├── tts/               # 音声合成
│   ├── llm/               # LLMクライアント
│   └── agent/             # エージェント
│
├── scripts/               # スクリプト
│   ├── setup.ps1          # セットアップ
│   └── start.ps1          # 起動
│
└── README.md
```

## 🔧 トラブルシューティング

### バックエンドが起動しない
```powershell
# 仮想環境の確認
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8765 --log-level debug
```

### Ollamaに接続できない
```powershell
# Ollamaの状態確認
ollama list
# モデルの再ダウンロード
ollama pull qwen2.5:7b
```

### 音声認識が動かない
- マイクの権限を確認
- `espeak-ng` がインストールされているか確認
- `faster-whisper` のインストール確認: `pip install faster-whisper`

### VRMモデルが表示されない
- `.vrm` ファイルが `electron/assets/models/` にあるか確認
- VRM 0.x / 1.0 形式に対応しています

## 📜 使用技術・モデル

| 項目 | 技術/モデル | ライセンス |
|:---|:---|:---|
| LLM | Ollamaでインストールした任意の対応モデル | モデルごとに異なります |
| STT | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT |
| TTS | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | Apache 2.0 |
| Agent | [smolagents](https://github.com/huggingface/smolagents) | Apache 2.0 |
| VRM | [@pixiv/three-vrm](https://github.com/pixiv/three-vrm) | MIT |
| Desktop | [Electron](https://www.electronjs.org/) | MIT |
