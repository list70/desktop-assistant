import bpy
import bmesh
import math
import os

# 1. Clear Scene
def clear_scene():
    """Clear all objects and collections from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for col in bpy.data.collections:
        if col.name != "Collection":
            bpy.data.collections.remove(col)

# 2. Materials
def create_materials():
    """Create all materials for the AURA character"""
    materials = {}
    
    def make_mat(name, color, emission=False):
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = color
            if emission:
                # Blender 4.x/5.x: 'Emission Color', Blender 3.x: 'Emission'
                emission_input = 'Emission Color' if 'Emission Color' in bsdf.inputs else 'Emission'
                bsdf.inputs[emission_input].default_value = color
                bsdf.inputs['Emission Strength'].default_value = 2.0
        materials[name] = mat
        
    # Hex to normalized RGBA approximation
    make_mat('Skin', (1.0, 0.82, 0.70, 1.0)) # warm peach
    make_mat('Hair', (0.54, 0.72, 0.91, 1.0)) # pastel blue
    make_mat('Eye', (0.20, 0.33, 0.66, 1.0)) # dark blue
    make_mat('Jacket', (0.94, 0.96, 1.0, 1.0)) # white
    make_mat('Skirt', (0.53, 0.80, 1.0, 1.0)) # light blue
    make_mat('Circuit', (0.0, 1.0, 0.86, 1.0), emission=True) # glowing cyan
    
    return materials

# 3. Create Meshes
def create_meshes(materials):
    """Build character out of primitives"""
    objects_to_join = []
    
    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(0, 0, 1.25))
    head = bpy.context.active_object
    head.scale = (1, 0.9, 0.9)
    head.name = 'Head'
    head.data.materials.append(materials['Skin'])
    objects_to_join.append(head)
    
    # Eyes
    for i, side in enumerate(['L', 'R']):
        x = -0.06 if i == 0 else 0.06
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=(x, -0.15, 1.25))
        eye = bpy.context.active_object
        eye.scale = (1, 0.5, 1.2)
        eye.name = f'Eye_{side}'
        eye.data.materials.append(materials['Eye'])
        objects_to_join.append(eye)
    
    # Mouth
    bpy.ops.mesh.primitive_plane_add(size=0.04, location=(0, -0.16, 1.18))
    mouth = bpy.context.active_object
    mouth.rotation_euler = (math.pi/2, 0, 0)
    mouth.name = 'Mouth'
    mouth.data.materials.append(materials['Skin']) # simplified
    objects_to_join.append(mouth)

    # Hair
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.20, location=(0, 0, 1.27))
    hair = bpy.context.active_object
    hair.scale = (1.05, 0.95, 0.95)
    hair.name = 'Hair'
    hair.data.materials.append(materials['Hair'])
    objects_to_join.append(hair)
    
    # Body (Jacket)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.85))
    body = bpy.context.active_object
    body.scale = (0.15, 0.1, 0.25)
    body.name = 'Torso'
    body.data.materials.append(materials['Jacket'])
    objects_to_join.append(body)

    # Skirt
    bpy.ops.mesh.primitive_cone_add(radius1=0.2, radius2=0.15, depth=0.15, location=(0, 0, 0.55))
    skirt = bpy.context.active_object
    skirt.name = 'Skirt'
    skirt.data.materials.append(materials['Skirt'])
    objects_to_join.append(skirt)

    # Legs & Boots
    for i, side in enumerate(['Left', 'Right']):
        x = -0.08 if i == 0 else 0.08
        bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.45, location=(x, 0, 0.25))
        leg = bpy.context.active_object
        leg.name = f'Leg_{side}'
        leg.data.materials.append(materials['Skin'])
        objects_to_join.append(leg)

        bpy.ops.mesh.primitive_cube_add(size=0.1, location=(x, -0.02, 0.05))
        boot = bpy.context.active_object
        boot.scale = (0.9, 1.2, 1)
        boot.name = f'Boot_{side}'
        boot.data.materials.append(materials['Skirt'])
        objects_to_join.append(boot)

    # Arms (T-Pose) & Hands
    for i, side in enumerate(['Left', 'Right']):
        x = -0.3 if i == 0 else 0.3
        bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.3, location=(x, 0, 1.0))
        arm = bpy.context.active_object
        arm.rotation_euler = (0, math.pi/2, 0)
        arm.name = f'Arm_{side}'
        arm.data.materials.append(materials['Skin'])
        objects_to_join.append(arm)
        
        hx = -0.5 if i == 0 else 0.5
        bpy.ops.mesh.primitive_cube_add(size=0.06, location=(hx, 0, 1.0))
        hand = bpy.context.active_object
        hand.name = f'Hand_{side}'
        hand.data.materials.append(materials['Skin'])
        objects_to_join.append(hand)
    
    return objects_to_join

def join_meshes(objects):
    """Join all meshes into a single object"""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    body = bpy.context.active_object
    body.name = 'Aura_Body'
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
    return body

def create_armature():
    """Create Humanoid Armature for VRM"""
    bpy.ops.object.armature_add(enter_editmode=True, align='WORLD', location=(0, 0, 0))
    arm_obj = bpy.context.active_object
    arm_obj.name = 'Armature'
    armature = arm_obj.data
    
    bpy.ops.armature.select_all(action='SELECT')
    bpy.ops.armature.delete()
    
    bones = {}
    def add_bone(name, head, tail, parent_name=None):
        bone = armature.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        if parent_name:
            bone.parent = armature.edit_bones[parent_name]
        bones[name] = bone
        return bone

    add_bone('Hips', (0, 0, 0.55), (0, 0, 0.65))
    add_bone('Spine', (0, 0, 0.65), (0, 0, 0.8), 'Hips')
    add_bone('Chest', (0, 0, 0.8), (0, 0, 0.9), 'Spine')
    add_bone('UpperChest', (0, 0, 0.9), (0, 0, 1.0), 'Chest')
    add_bone('Neck', (0, 0, 1.0), (0, 0, 1.1), 'UpperChest')
    add_bone('Head', (0, 0, 1.1), (0, 0, 1.25), 'Neck')
    add_bone('LeftEye', (-0.06, -0.1, 1.25), (-0.06, -0.2, 1.25), 'Head')
    add_bone('RightEye', (0.06, -0.1, 1.25), (0.06, -0.2, 1.25), 'Head')
    
    add_bone('LeftShoulder', (0.05, 0, 1.0), (0.15, 0, 1.0), 'UpperChest')
    add_bone('LeftUpperArm', (0.15, 0, 1.0), (0.3, 0, 1.0), 'LeftShoulder')
    add_bone('LeftLowerArm', (0.3, 0, 1.0), (0.45, 0, 1.0), 'LeftUpperArm')
    add_bone('LeftHand', (0.45, 0, 1.0), (0.55, 0, 1.0), 'LeftLowerArm')
    
    add_bone('RightShoulder', (-0.05, 0, 1.0), (-0.15, 0, 1.0), 'UpperChest')
    add_bone('RightUpperArm', (-0.15, 0, 1.0), (-0.3, 0, 1.0), 'RightShoulder')
    add_bone('RightLowerArm', (-0.3, 0, 1.0), (-0.45, 0, 1.0), 'RightUpperArm')
    add_bone('RightHand', (-0.45, 0, 1.0), (-0.55, 0, 1.0), 'RightLowerArm')

    add_bone('LeftUpperLeg', (0.08, 0, 0.55), (0.08, 0, 0.25), 'Hips')
    add_bone('LeftLowerLeg', (0.08, 0, 0.25), (0.08, 0, 0.1), 'LeftUpperLeg')
    add_bone('LeftFoot', (0.08, 0, 0.1), (0.08, -0.1, 0), 'LeftLowerLeg')
    add_bone('LeftToes', (0.08, -0.1, 0), (0.08, -0.15, 0), 'LeftFoot')

    add_bone('RightUpperLeg', (-0.08, 0, 0.55), (-0.08, 0, 0.25), 'Hips')
    add_bone('RightLowerLeg', (-0.08, 0, 0.25), (-0.08, 0, 0.1), 'RightUpperLeg')
    add_bone('RightFoot', (-0.08, 0, 0.1), (-0.08, -0.1, 0), 'RightLowerLeg')
    add_bone('RightToes', (-0.08, -0.1, 0), (-0.08, -0.15, 0), 'RightFoot')

    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj

def add_shape_keys(body):
    """Add empty shape keys for VRM expressions"""
    sk_basis = body.shape_key_add(name='Basis')
    sk_basis.interpolation = 'KEY_LINEAR'
    
    shapes = ['Blink', 'BlinkLeft', 'BlinkRight', 'Happy', 'Sad', 'Surprised', 'Angry', 'Aa', 'Ih', 'Ou', 'Ee', 'Oh']
    for shape in shapes:
        body.shape_key_add(name=shape)

def setup_vrm_metadata(armature):
    """Set VRM custom properties"""
    armature['title'] = 'AURA - AI Assistant'
    armature['author'] = 'Desktop Assistant Project'
    armature['version'] = '1.0'

def export_glb():
    """Export the scene to GLB format"""
    target_dir = r"C:\Users\yutal\OneDrive\デスクトップ\desktop-assistant\blender"
    try:
        if '__file__' in globals():
            f_dir = os.path.dirname(os.path.abspath(__file__))
            if os.path.exists(f_dir) and f_dir != "C:\\":
                target_dir = f_dir
    except Exception:
        pass
    
    os.makedirs(target_dir, exist_ok=True)
    out_path = os.path.join(target_dir, 'aura_character.glb')
    bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
    print(f"Exported to {out_path}")

if __name__ == "__main__":
    clear_scene()
    materials = create_materials()
    objects = create_meshes(materials)
    body = join_meshes(objects)
    armature = create_armature()
    
    # Parent with automatic weights
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    
    add_shape_keys(body)
    setup_vrm_metadata(armature)
    export_glb()
