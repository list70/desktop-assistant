"""
AURA VRM 変換スクリプト
========================
GLBファイルをVRMに変換する。VRM Add-on for Blenderが必要。
ヒューマノイドボーンのマッピングとVRMメタデータの設定を行う。

使い方:
  Blenderのスクリプトエディタで開いて実行する。
  先に create_character.py を実行して aura_character.glb を生成しておくこと。
"""

import bpy
import os


def convert_to_vrm():
    script_dir = r"C:\Users\yutal\OneDrive\デスクトップ\desktop-assistant\blender"
    try:
        if '__file__' in globals():
            f_dir = os.path.dirname(os.path.abspath(__file__))
            if os.path.exists(f_dir) and f_dir != "C:\\":
                script_dir = f_dir
    except Exception:
        pass

    glb_path = os.path.join(script_dir, 'aura_character.glb')
    vrm_path = r'c:\Users\yutal\OneDrive\デスクトップ\desktop-assistant\electron\assets\models\aura.vrm'

    # 出力先ディレクトリの作成
    os.makedirs(os.path.dirname(vrm_path), exist_ok=True)

    # シーンをクリア
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # GLBをインポート
    if not os.path.exists(glb_path):
        print(f"ERROR: GLBファイルが見つかりません: {glb_path}")
        print("先に create_character.py を実行してください。")
        return

    bpy.ops.import_scene.gltf(filepath=glb_path)

    # アーマチュアを検索
    armature = None
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break

    if not armature:
        print("ERROR: アーマチュアが見つかりません。GLBにアーマチュアが含まれているか確認してください。")
        return

    bpy.context.view_layer.objects.active = armature

    # -------------------------------------------------------
    # VRM ヒューマノイドボーンマッピング
    # -------------------------------------------------------
    # VRM Add-on が有効な場合、vrm_addon_extension が利用可能
    try:
        vrm_ext = armature.data.vrm_addon_extension

        # VRM バージョン設定 (VRM 1.0)
        vrm_ext.spec_version = "1.0"

        # メタデータ設定
        meta = vrm_ext.vrm1.meta
        meta.vrm_name = "AURA - AI Assistant"
        meta.authors.clear()
        author = meta.authors.add()
        author.value = "Desktop Assistant Project"
        meta.version = "1.0"
        meta.allow_redistribution = True

        # ヒューマノイドボーンマッピング
        humanoid = vrm_ext.vrm1.humanoid
        bone_mapping = {
            "hips": "Hips",
            "spine": "Spine",
            "chest": "Chest",
            "upperChest": "UpperChest",
            "neck": "Neck",
            "head": "Head",
            "leftEye": "LeftEye",
            "rightEye": "RightEye",
            "leftShoulder": "LeftShoulder",
            "leftUpperArm": "LeftUpperArm",
            "leftLowerArm": "LeftLowerArm",
            "leftHand": "LeftHand",
            "rightShoulder": "RightShoulder",
            "rightUpperArm": "RightUpperArm",
            "rightLowerArm": "RightLowerArm",
            "rightHand": "RightHand",
            "leftUpperLeg": "LeftUpperLeg",
            "leftLowerLeg": "LeftLowerLeg",
            "leftFoot": "LeftFoot",
            "leftToes": "LeftToes",
            "rightUpperLeg": "RightUpperLeg",
            "rightLowerLeg": "RightLowerLeg",
            "rightFoot": "RightFoot",
            "rightToes": "RightToes",
        }

        for vrm_bone_name, blender_bone_name in bone_mapping.items():
            human_bone = getattr(humanoid.human_bones, vrm_bone_name, None)
            if human_bone is not None:
                human_bone.node.bone_name = blender_bone_name

        print("VRM ヒューマノイドボーンマッピング完了")

        # -------------------------------------------------------
        # VRM エクスプレッション設定
        # -------------------------------------------------------
        expressions = vrm_ext.vrm1.expressions

        # シェイプキーとVRMエクスプレッションの対応
        expression_mapping = {
            "happy": "Happy",
            "angry": "Angry",
            "sad": "Sad",
            "relaxed": "Neutral",      # fallback
            "surprised": "Surprised",
            "blink": "Blink",
            "blinkLeft": "BlinkLeft",
            "blinkRight": "BlinkRight",
            "aa": "Aa",
            "ih": "Ih",
            "ou": "Ou",
            "ee": "Ee",
            "oh": "Oh",
        }

        # メッシュオブジェクトを検索
        mesh_obj = None
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.data.shape_keys:
                mesh_obj = obj
                break

        if mesh_obj:
            for vrm_expr_name, shape_key_name in expression_mapping.items():
                preset = getattr(expressions, vrm_expr_name, None)
                if preset is not None and hasattr(preset, 'morph_target_binds'):
                    if shape_key_name in mesh_obj.data.shape_keys.key_blocks:
                        bind = preset.morph_target_binds.add()
                        bind.node.mesh_object_name = mesh_obj.name
                        bind.index = shape_key_name
                        bind.weight = 1.0

            print("VRM エクスプレッション設定完了")
        else:
            print("WARNING: シェイプキー付きメッシュが見つかりませんでした")

    except AttributeError as e:
        print(f"WARNING: VRM Add-on APIが利用できません: {e}")
        print("VRM Add-on for Blenderがインストール・有効化されているか確認してください。")
        print("アドオンなしで直接GLBとしてエクスポートします。")

        # フォールバック: GLBのまま出力
        fallback_path = vrm_path.replace('.vrm', '.glb')
        bpy.ops.export_scene.gltf(filepath=fallback_path, export_format='GLB')
        print(f"GLBとしてエクスポート: {fallback_path}")
        return

    # -------------------------------------------------------
    # VRM エクスポート
    # -------------------------------------------------------
    try:
        bpy.ops.export_scene.vrm(filepath=vrm_path)
        print(f"VRMエクスポート成功: {vrm_path}")
    except Exception as e:
        print(f"VRMエクスポート失敗: {e}")
        print("GLBフォーマットでフォールバックエクスポートします...")
        fallback_path = vrm_path.replace('.vrm', '.glb')
        bpy.ops.export_scene.gltf(filepath=fallback_path, export_format='GLB')
        print(f"GLBとしてエクスポート: {fallback_path}")


if __name__ == "__main__":
    convert_to_vrm()
