# AURA キャラクター生成スクリプト

BlenderでAURA AIアシスタントの3Dモデルを自動生成し、VRM形式でエクスポートするスクリプトです。

## 必要なもの

- **Blender 5.2** (4.x でも動作します)
- **VRM format アドオン** — [Blender Extensions](https://extensions.blender.org/add-ons/vrm/) からインストール

### VRM アドオンのインストール方法

1. Blender を開く
2. **Edit → Preferences → Get Extensions**
3. 検索欄に「VRM」と入力
4. **「VRM format」** をインストール
5. 有効化を確認（チェックマークが付いていればOK）

## 使い方

### ステップ 1: キャラクター生成 → GLBエクスポート

1. Blender を開く
2. **Scripting** ワークスペースに切り替え（画面上部のタブ）
3. **Open** ボタンで以下のファイルを開く:
   ```
   c:\Users\yutal\OneDrive\デスクトップ\desktop-assistant\blender\create_character.py
   ```
4. **▶ Run Script** ボタンをクリック
5. `blender/aura_character.glb` が生成される

### ステップ 2: VRM に変換

1. 同じ Blender セッション（または新しいセッション）で
2. **Scripting** ワークスペースで以下を開く:
   ```
   c:\Users\yutal\OneDrive\デスクトップ\desktop-assistant\blender\convert_to_vrm.py
   ```
3. **▶ Run Script** ボタンをクリック
4. `electron/assets/models/aura.vrm` が生成される

### ステップ 3: デスクトップアシスタントで確認

```powershell
cd c:\Users\yutal\OneDrive\デスクトップ\desktop-assistant
.\scripts\start.ps1
```

起動するとAURAが自動的に表示されます！

## カスタマイズ

### 色を変える

`create_character.py` の `create_materials()` 関数でRGBA値を変更:

```python
make_mat('Hair', (0.54, 0.72, 0.91, 1.0))  # パステルブルー → 好きな色に
make_mat('Eye', (0.20, 0.33, 0.66, 1.0))   # 紫/青の目
make_mat('Jacket', (0.94, 0.96, 1.0, 1.0)) # 白ジャケット
make_mat('Skirt', (0.53, 0.80, 1.0, 1.0))  # 水色スカート
make_mat('Circuit', (0.0, 1.0, 0.86, 1.0), emission=True) # 発光シアン
```

### サイズ・プロポーションを変える

`create_meshes()` 関数で各パーツのサイズを調整:

```python
# 頭を大きくする（デフォルメ強め）
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, ...)  # 0.18 → 0.22

# 体を小さくする
body.scale = (0.12, 0.08, 0.20)  # (0.15, 0.1, 0.25) → 小さく
```

## トラブルシューティング

### 「VRM export operator not found」エラー
→ VRM format アドオンがインストール・有効化されていない
→ Edit → Preferences → Get Extensions で「VRM」を検索してインストール

### 出力先ディレクトリがない
→ スクリプトが自動作成しますが、権限エラーの場合は手動で作成:
```powershell
mkdir "c:\Users\yutal\OneDrive\デスクトップ\desktop-assistant\electron\assets\models"
```

### 自動ウェイトが失敗する
→ メッシュとアーマチュアの位置がずれている可能性
→ スクリプトを再実行する前に **File → New → General** で新しいシーンにする
