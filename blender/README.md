# AURA キャラクター

正面・横・後ろの三面図を参照して作成した、デフォルメ調のAURAモデルです。

## ファイル

- `aura_character_design_sheet.svg` — キャラクター三面図
- `build_aura_character.py` — Blenderでモデル、リグ、表情キーを生成するスクリプト
- `aura_character.blend` — 編集用Blenderプロジェクト。三面図はテキストデータとして同梱
- `aura_character.glb` — GLB出力
- `aura_character.vrm` — VRM 1.0出力
- `aura_character_preview.png` — レンダープレビュー
- `../electron/assets/models/aura.vrm` — アプリで読み込むVRM

モデルには24本のHumanoidボーンと、まばたき、喜怒哀楽、母音などの表情キーを設定しています。

## 必要なもの

- Blender 5.2
- 公式 [VRM format アドオン](https://extensions.blender.org/add-ons/vrm/)。BlenderのPreferences → Get Extensionsで「VRM format」をインストールして有効化します。

## 生成

BlenderのScriptingワークスペースで `build_aura_character.py` を開き、Run Scriptを実行します。WindowsのPowerShellから実行する場合は、リポジトリのルートで:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
& $blender -b --python ".\blender\build_aura_character.py"
```

スクリプトは `.blend`、`.glb`、`.vrm`、プレビュー画像を生成し、VRMアドオンが有効ならアプリ用の `electron/assets/models/aura.vrm` も更新します。
