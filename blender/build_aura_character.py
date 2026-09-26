"""Build the AURA desktop-assistant avatar in Blender.

Run this file from Blender's Python Console or Text Editor.  The model is made
from smooth, named mesh parts so it stays easy to edit, and the humanoid
armature uses VRM 1.0 bone assignments when the VRM add-on is enabled.
"""

import math
import os
import shutil
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


_script_path = globals().get("__file__")
if _script_path:
    BLENDER_DIR = Path(_script_path).resolve().parent
elif bpy.data.filepath:
    BLENDER_DIR = Path(bpy.data.filepath).resolve().parent
else:
    raise RuntimeError("Run this script from disk or from a saved Blender project.")
ROOT = BLENDER_DIR.parent
MODELS_DIR = ROOT / "electron" / "assets" / "models"
DESIGN_SHEET = BLENDER_DIR / "aura_character_design_sheet.svg"
BLEND_PATH = BLENDER_DIR / "aura_character.blend"
GLB_PATH = BLENDER_DIR / "aura_character.glb"
PREVIEW_PATH = BLENDER_DIR / "aura_character_preview.png"
VRM_PATH = BLENDER_DIR / "aura_character.vrm"
APP_VRM_PATH = MODELS_DIR / "aura.vrm"


# -----------------------------------------------------------------------------
# Scene and materials
# -----------------------------------------------------------------------------

def clear_scene():
    active = bpy.context.object
    if active and active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    root = bpy.context.scene.collection
    for child in list(root.children):
        if child.name == "Collection":
            root.children.unlink(child)
            if child.users == 0:
                bpy.data.collections.remove(child)


def new_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def make_material(name, color, roughness=0.66, metallic=0.0, emission=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    shader = next((node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if shader is None:
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        output = next((node for node in nodes if node.bl_idname == "ShaderNodeOutputMaterial"), None)
        if output is None:
            output = nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if emission:
        emission_color = "Emission Color" if "Emission Color" in shader.inputs else "Emission"
        shader.inputs[emission_color].default_value = (*color, 1.0)
        shader.inputs["Emission Strength"].default_value = emission
    material["AURA_Palette"] = True
    return material


def make_palette():
    return {
        "skin": make_material("Skin | warm peach", (0.98, 0.70, 0.61), 0.78),
        "skin_shadow": make_material("Skin | soft rose", (0.91, 0.47, 0.48), 0.76),
        "hair": make_material("Hair | powder blue", (0.12, 0.36, 0.66), 0.38),
        "hair_light": make_material("Hair | ice highlight", (0.47, 0.79, 0.92), 0.4),
        "hair_dark": make_material("Hair | shaded blue", (0.16, 0.34, 0.61), 0.48),
        "eye_white": make_material("Eyes | porcelain", (0.95, 0.99, 1.0), 0.28),
        "iris": make_material("Eyes | ocean blue", (0.08, 0.36, 0.77), 0.25, metallic=0.05),
        "iris_light": make_material("Eyes | aqua rim", (0.12, 0.78, 0.86), 0.26),
        "pupil": make_material("Eyes | deep navy", (0.035, 0.075, 0.19), 0.22),
        "shine": make_material("Eyes | bright glint", (1.0, 1.0, 1.0), 0.16, emission=0.25),
        "ink": make_material("Face | blue ink", (0.10, 0.18, 0.34), 0.55),
        "coat": make_material("Jacket | pearl white", (0.91, 0.96, 0.98), 0.72),
        "coat_light": make_material("Jacket | ivory panel", (0.99, 0.98, 0.92), 0.72),
        "coat_shadow": make_material("Jacket | blue-gray panel", (0.66, 0.81, 0.91), 0.7),
        "skirt": make_material("Skirt | sky blue", (0.31, 0.64, 0.86), 0.58),
        "skirt_light": make_material("Skirt | pleat highlight", (0.53, 0.79, 0.93), 0.56),
        "navy": make_material("Boots | deep blue", (0.15, 0.28, 0.48), 0.55),
        "cyan": make_material("Trim | luminous cyan", (0.11, 0.75, 0.81), 0.38, emission=0.22),
        "gold": make_material("Accent | soft gold", (0.92, 0.69, 0.31), 0.42, metallic=0.42),
        "mouth": make_material("Mouth | berry", (0.47, 0.11, 0.20), 0.54),
        "tongue": make_material("Mouth | rose", (0.91, 0.31, 0.42), 0.55),
        "teeth": make_material("Mouth | warm white", (1.0, 0.94, 0.83), 0.4),
    }


def recalc_mesh_normals(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    if bm.faces:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def create_mesh(name, vertices, faces, materials, collection, material_indices=None, location=(0, 0, 0), smooth=True):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    for material in materials:
        mesh.materials.append(material)
    mesh.update()
    if material_indices:
        for index, polygon in enumerate(mesh.polygons):
            if index < len(material_indices):
                polygon.material_index = material_indices[index]
    recalc_mesh_normals(mesh)
    if smooth:
        for polygon in mesh.polygons:
            polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.location = location
    return obj


def sphere_geometry(vertices, faces, material_indices, center, radii, material_index, segments=24, rings=16):
    """Append a UV sphere in mesh-local coordinates and return its vertex range."""
    start = len(vertices)
    cx, cy, cz = center
    rx, ry, rz = radii
    vertices.append((cx, cy, cz + rz))
    top = start
    ring_starts = []
    for ring in range(1, rings):
        theta = math.pi * ring / rings
        ring_starts.append(len(vertices))
        for segment in range(segments):
            phi = 2.0 * math.pi * segment / segments
            vertices.append((cx + rx * math.sin(theta) * math.cos(phi),
                             cy + ry * math.sin(theta) * math.sin(phi),
                             cz + rz * math.cos(theta)))
    bottom = len(vertices)
    vertices.append((cx, cy, cz - rz))
    for segment in range(segments):
        faces.append((top, ring_starts[0] + segment, ring_starts[0] + (segment + 1) % segments))
        material_indices.append(material_index)
    for ring in range(len(ring_starts) - 1):
        upper = ring_starts[ring]
        lower = ring_starts[ring + 1]
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append((upper + segment, lower + segment, lower + next_segment, upper + next_segment))
            material_indices.append(material_index)
    last = ring_starts[-1]
    for segment in range(segments):
        faces.append((last + segment, bottom, last + (segment + 1) % segments))
        material_indices.append(material_index)
    return range(start, len(vertices))


def add_ellipsoid(name, center, radii, material, collection, parent_bone=None, rotation=None, segments=24, rings=16):
    vertices, faces, ids = [], [], []
    sphere_geometry(vertices, faces, ids, (0, 0, 0), radii, 0, segments, rings)
    obj = create_mesh(name, vertices, faces, [material], collection, ids, location=center)
    if rotation:
        obj.rotation_euler = rotation
    if parent_bone:
        obj["AURA_parent_bone"] = parent_bone
    obj["AURA_part"] = name
    return obj


def add_lathe(name, profile, material, collection, segments=32, material_by_ring=None, parent_bone=None):
    vertices, faces, ids = [], [], []
    for z, rx, ry in profile:
        for segment in range(segments):
            angle = 2.0 * math.pi * segment / segments
            vertices.append((rx * math.cos(angle), ry * math.sin(angle), z))
    for ring in range(len(profile) - 1):
        for segment in range(segments):
            nxt = (segment + 1) % segments
            faces.append((ring * segments + segment,
                          ring * segments + nxt,
                          (ring + 1) * segments + nxt,
                          (ring + 1) * segments + segment))
            ids.append(material_by_ring[ring] if material_by_ring else 0)
    faces.append(tuple(reversed(range(segments))))
    ids.append(material_by_ring[0] if material_by_ring else 0)
    faces.append(tuple((len(profile) - 1) * segments + i for i in range(segments)))
    ids.append(material_by_ring[-1] if material_by_ring else 0)
    obj = create_mesh(name, vertices, faces, [material] if not isinstance(material, (list, tuple)) else material, collection, ids)
    if parent_bone:
        obj["AURA_parent_bone"] = parent_bone
    return obj


def add_torus(name, center, radius_x, radius_y, tube_radius, material, collection, parent_bone=None, segments=40, sides=8, axis=None):
    vertices, faces, ids = [], [], []
    axis = Vector(axis or (0, 0, 1)).normalized()
    reference = Vector((0, 1, 0)) if abs(axis.dot(Vector((0, 1, 0)))) < 0.92 else Vector((1, 0, 0))
    u = axis.cross(reference).normalized()
    v = axis.cross(u).normalized()
    origin = Vector(center)
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        radial = u * math.cos(theta) + v * math.sin(theta)
        mid = origin + u * (radius_x * math.cos(theta)) + v * (radius_y * math.sin(theta))
        for j in range(sides):
            phi = 2 * math.pi * j / sides
            point = mid + radial * (tube_radius * math.cos(phi)) + axis * (tube_radius * math.sin(phi))
            vertices.append(tuple(point))
    for i in range(segments):
        for j in range(sides):
            a = i * sides + j
            b = ((i + 1) % segments) * sides + j
            c = ((i + 1) % segments) * sides + (j + 1) % sides
            d = i * sides + (j + 1) % sides
            faces.append((a, b, c, d))
            ids.append(0)
    obj = create_mesh(name, vertices, faces, [material], collection, ids, smooth=True)
    if parent_bone:
        obj["AURA_parent_bone"] = parent_bone
    return obj


def add_segment(name, start, end, radius, material, collection, parent_bone, depth_ratio=0.88):
    start_v, end_v = Vector(start), Vector(end)
    direction = end_v - start_v
    midpoint = (start_v + end_v) * 0.5
    length = direction.length
    rotation = Vector((0, 0, 1)).rotation_difference(direction.normalized()).to_euler()
    obj = add_ellipsoid(name, midpoint, (radius, radius * depth_ratio, length * 0.5 + radius * 0.25), material, collection, parent_bone, rotation)
    return obj


def add_tube(name, points, radii, material, collection, parent_bone=None, sides=8):
    """Mesh a gently curved tube through 3D control points with tapering radii."""
    path = [Vector(point) for point in points]
    vertices, faces, ids = [], [], []
    tangents = []
    for i in range(len(path)):
        if i == 0:
            tangent = path[1] - path[0]
        elif i == len(path) - 1:
            tangent = path[-1] - path[-2]
        else:
            tangent = path[i + 1] - path[i - 1]
        tangents.append(tangent.normalized())
    previous_u = None
    for i, point in enumerate(path):
        tangent = tangents[i]
        ref = Vector((0, 1, 0))
        if abs(tangent.dot(ref)) > 0.92:
            ref = Vector((1, 0, 0))
        u = tangent.cross(ref).normalized()
        if previous_u is not None and u.dot(previous_u) < 0:
            u.negate()
        v = tangent.cross(u).normalized()
        previous_u = u
        for j in range(sides):
            angle = 2.0 * math.pi * j / sides
            offset = radii[i] * (u * math.cos(angle) + v * math.sin(angle))
            vertices.append(tuple(point + offset))
    for i in range(len(path) - 1):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            c = (i + 1) * sides + (j + 1) % sides
            d = (i + 1) * sides + j
            faces.append((a, b, c, d))
            ids.append(0)
    obj = create_mesh(name, vertices, faces, [material], collection, ids, smooth=True)
    if parent_bone:
        obj["AURA_parent_bone"] = parent_bone
    return obj


def add_bezier_tuft(name, p0, p1, p2, p3, width, material, collection, parent_bone="head", steps=14, sides=10):
    controls = [Vector(p) for p in (p0, p1, p2, p3)]
    points, radii = [], []
    for i in range(steps):
        t = i / (steps - 1)
        s = 1.0 - t
        point = s**3 * controls[0] + 3*s*s*t * controls[1] + 3*s*t*t * controls[2] + t**3 * controls[3]
        points.append(tuple(point))
        radii.append(width * (0.20 + 0.80 * math.sin(math.pi * (0.1 + 0.84 * t))) * (1.0 - 0.92 * t))
    return add_tube(name, points, radii, material, collection, parent_bone, sides)


def add_ribbon(name, points, width, material, collection, parent_bone=None):
    """Create a thin raised line following points, suitable for seams and lashes."""
    vectors = [Vector(point) for point in points]
    vertices, faces = [], []
    for i, point in enumerate(vectors):
        tangent = vectors[min(i + 1, len(vectors) - 1)] - vectors[max(0, i - 1)]
        side = Vector((-tangent.z, 0, tangent.x))
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        vertices.extend((tuple(point + side * width), tuple(point - side * width)))
    for i in range(len(vectors) - 1):
        faces.append((2*i, 2*i+1, 2*i+3, 2*i+2))
    obj = create_mesh(name, vertices, faces, [material], collection, smooth=False)
    if parent_bone:
        obj["AURA_parent_bone"] = parent_bone
    return obj


def make_morphed_eye(name, center, palette, collection, side_sign):
    """A unified eye mesh with open, blink, happy, sad, angry and surprised keys."""
    vertices, faces, ids = [], [], []
    parts = {}
    eye_scale = 0.84
    def scaled(radii):
        return tuple(component * eye_scale for component in radii)
    parts["white"] = sphere_geometry(vertices, faces, ids, (0, 0, 0), scaled((0.069, 0.023, 0.084)), 0)
    parts["iris_rim"] = sphere_geometry(vertices, faces, ids, (0, -0.016, -0.004), scaled((0.047, 0.013, 0.060)), 1)
    parts["iris"] = sphere_geometry(vertices, faces, ids, (0, -0.022, -0.003), scaled((0.040, 0.011, 0.053)), 2)
    parts["pupil"] = sphere_geometry(vertices, faces, ids, (0, -0.029, -0.005), scaled((0.024, 0.007, 0.037)), 3)
    parts["shine_big"] = sphere_geometry(vertices, faces, ids, (-0.012, -0.035, 0.014), scaled((0.012, 0.0045, 0.017)), 4, 16, 10)
    parts["shine_small"] = sphere_geometry(vertices, faces, ids, (0.014, -0.035, -0.020), scaled((0.0055, 0.003, 0.008)), 4, 16, 10)

    # Arched upper eyelash, shaped into a closed lid by the blink keys.
    lash_start = len(vertices)
    lash_width = 0.071
    count = 13
    for i in range(count):
        x = -lash_width + (2 * lash_width * i / (count - 1))
        t = x / lash_width
        z = 0.048 + 0.037 * (1.0 - t * t)
        vertices.extend(((x, -0.041, z + 0.004), (x, -0.041, z - 0.004)))
    for i in range(count - 1):
        faces.append((lash_start + 2*i, lash_start + 2*i+1, lash_start + 2*i+3, lash_start + 2*i+2))
        ids.append(5)
    parts["lash"] = range(lash_start, len(vertices))

    # Brows are part of the same morph target so expression keys move them too.
    brow_start = len(vertices)
    brow_width = 0.046
    for i in range(11):
        x = -brow_width + 2 * brow_width * i / 10
        t = x / brow_width
        z = 0.104 + 0.010 * (1.0 - t * t)
        thickness = 0.0035 * (0.42 + 0.58 * math.sin(math.pi * i / 10))
        vertices.extend(((x, -0.009, z + thickness), (x, -0.009, z - thickness)))
    for i in range(10):
        faces.append((brow_start + 2*i, brow_start + 2*i+1, brow_start + 2*i+3, brow_start + 2*i+2))
        ids.append(5)
    parts["brow"] = range(brow_start, len(vertices))

    materials = [palette["eye_white"], palette["iris_light"], palette["iris"], palette["pupil"], palette["shine"], palette["ink"]]
    obj = create_mesh(name, vertices, faces, materials, collection, ids, location=center)
    obj["AURA_parent_bone"] = "head"
    basis = obj.shape_key_add(name="Basis")

    def add_key(key_name, eye_scale=1.0, lash_mode="open", brow_mode="neutral"):
        key = obj.shape_key_add(name=key_name)
        for index, point in enumerate(basis.data):
            co = point.co.copy()
            if index in parts["lash"]:
                if lash_mode == "closed":
                    co.z = -0.002 + 0.006 * (co.x / lash_width) ** 2
                elif lash_mode == "happy":
                    co.z = -0.006 + 0.013 * (co.x / lash_width) ** 2
                elif lash_mode == "sad":
                    co.z = 0.008 + 0.006 * (co.x / lash_width) ** 2
            else:
                if index < lash_start:
                    center_z = 0.0
                    co.z = center_z + co.z * eye_scale
                if index in parts["brow"]:
                    if brow_mode == "angry":
                        co.z -= side_sign * co.x * 0.62
                    elif brow_mode == "sad":
                        co.z += side_sign * co.x * 0.52 + 0.006
                    elif brow_mode == "surprised":
                        co.z += 0.022
                    elif brow_mode == "happy":
                        co.z += 0.006
            key.data[index].co = co
        return key

    add_key("Blink", eye_scale=0.035, lash_mode="closed")
    add_key("BlinkLeft", eye_scale=0.035 if side_sign > 0 else 1.0, lash_mode="closed" if side_sign > 0 else "open")
    add_key("BlinkRight", eye_scale=0.035 if side_sign < 0 else 1.0, lash_mode="closed" if side_sign < 0 else "open")
    add_key("Happy", eye_scale=0.16, lash_mode="happy", brow_mode="happy")
    add_key("Sad", eye_scale=0.76, lash_mode="sad", brow_mode="sad")
    add_key("Angry", eye_scale=0.78, lash_mode="open", brow_mode="angry")
    add_key("Surprised", eye_scale=1.22, lash_mode="open", brow_mode="surprised")
    for shape_key in obj.data.shape_keys.key_blocks:
        if shape_key.name != "Basis":
            shape_key.value = 0.0
    return obj


def make_morphed_mouth(palette, collection):
    vertices, faces, ids = [], [], []
    parts = {}
    parts["cavity"] = sphere_geometry(vertices, faces, ids, (0, 0, 0), (0.032, 0.007, 0.0065), 0)
    parts["teeth"] = sphere_geometry(vertices, faces, ids, (0, -0.003, 0.002), (0.017, 0.0025, 0.0023), 1, 16, 10)
    parts["tongue"] = sphere_geometry(vertices, faces, ids, (0, -0.003, -0.0025), (0.014, 0.0026, 0.003), 2, 16, 10)
    obj = create_mesh("Mouth_Expressions", vertices, faces,
                      [palette["mouth"], palette["teeth"], palette["tongue"]], collection, ids,
                      location=(0, -0.169, 0.833))
    obj["AURA_parent_bone"] = "head"
    basis = obj.shape_key_add(name="Basis")
    configs = {
        "Happy": (1.48, 2.1, 0.25, 1.00),
        "Sad": (0.92, 1.75, -0.30, 0.72),
        "Angry": (0.88, 0.70, -0.12, 0.28),
        "Surprised": (0.92, 2.9, 0.00, 1.00),
        "Aa": (1.25, 2.9, 0.00, 1.00),
        "Ih": (1.70, 1.15, 0.00, 0.9),
        "Ou": (0.78, 2.8, 0.00, 1.0),
        "Ee": (1.85, 0.86, 0.08, 0.55),
        "Oh": (0.94, 2.7, 0.00, 1.0),
        "Relaxed": (0.85, 0.72, 0.05, 0.2),
    }
    for name, (sx, sz, curve, interior) in configs.items():
        key = obj.shape_key_add(name=name)
        for index, point in enumerate(basis.data):
            co = point.co.copy()
            if index in parts["cavity"]:
                x = co.x * sx
                z = co.z * sz
                z += curve * (abs(point.co.x) / 0.032) ** 2 * 0.0045
                co.x, co.z = x, z
            elif index in parts["teeth"] or index in parts["tongue"]:
                co.x = point.co.x * sx
                co.z = point.co.z * interior
            key.data[index].co = co
    for shape_key in obj.data.shape_keys.key_blocks:
        if shape_key.name != "Basis":
            shape_key.value = 0.0
    return obj


# -----------------------------------------------------------------------------
# Character construction
# -----------------------------------------------------------------------------

def build_body(palette, char_collection):
    # Jacket torso is a softly contoured, shallow pear silhouette.
    torso = add_lathe(
        "Jacket_Torso",
        [(0.405, 0.105, 0.075), (0.43, 0.133, 0.087), (0.52, 0.126, 0.087),
         (0.64, 0.146, 0.095), (0.735, 0.142, 0.084), (0.775, 0.112, 0.073)],
        palette["coat"], char_collection, segments=32, parent_bone="chest")
    torso["AURA_part"] = "Pearl tech jacket"
    # Front jacket panels, small tie tab, buttons, badge, and pocket flaps.
    add_ellipsoid("Jacket_ChestPanel", (0, -0.083, 0.63), (0.109, 0.012, 0.132), palette["coat_light"], char_collection, "chest")
    add_ellipsoid("Jacket_Tie", (0, -0.101, 0.62), (0.020, 0.009, 0.088), palette["skirt"], char_collection, "chest")
    add_ellipsoid("Jacket_TieKnot", (0, -0.110, 0.70), (0.020, 0.010, 0.020), palette["cyan"], char_collection, "chest")
    add_ellipsoid("Jacket_LeftLapel", (-0.045, -0.094, 0.714), (0.041, 0.009, 0.068), palette["coat_light"], char_collection, "chest", rotation=(0, -0.24, -0.12))
    add_ellipsoid("Jacket_RightLapel", (0.045, -0.094, 0.714), (0.041, 0.009, 0.068), palette["coat_light"], char_collection, "chest", rotation=(0, 0.24, 0.12))
    for z in (0.545, 0.585, 0.625):
        add_ellipsoid("Jacket_Button", (0.012, -0.112, z), (0.0075, 0.004, 0.0075), palette["gold"], char_collection, "chest", segments=16, rings=10)
    add_ellipsoid("Jacket_Crest", (-0.090, -0.100, 0.680), (0.019, 0.008, 0.023), palette["cyan"], char_collection, "chest", segments=16, rings=10)
    # Raised chest piping and a clear waist trim.
    add_tube("Jacket_CyanHem", [(-0.12, -0.073, 0.429), (-0.07, -0.089, 0.414), (0, -0.093, 0.407), (0.07, -0.089, 0.414), (0.12, -0.073, 0.429)],
             [0.0035] * 5, palette["cyan"], char_collection, "chest")
    for sign in (-1, 1):
        add_ellipsoid("Jacket_Pocket", (sign * 0.079, -0.095, 0.556), (0.029, 0.009, 0.024), palette["coat_shadow"], char_collection, "chest", rotation=(0, 0, sign * 0.04))
        add_tube("Jacket_PocketStitch", [(sign * 0.052, -0.103, 0.569), (sign * 0.079, -0.104, 0.573), (sign * 0.106, -0.099, 0.569)],
                 [0.0016] * 3, palette["coat_light"], char_collection, "chest", sides=6)
    # Back seams add a tailored jacket silhouette on the reverse view.
    add_tube("Jacket_BackSeam", [(0, 0.091, 0.76), (0, 0.098, 0.67), (0, 0.093, 0.55), (0, 0.080, 0.43)],
             [0.0018] * 4, palette["coat_shadow"], char_collection, "chest")
    for x in (-0.082, 0.082):
        add_tube("Jacket_BackDart", [(x, 0.066, 0.60), (x * 0.75, 0.089, 0.52), (x * 0.78, 0.078, 0.44)],
                 [0.0015] * 3, palette["coat_shadow"], char_collection, "chest")

    # Short pleated skirt with radial profile and a soft pearl hem.
    skirt = add_lathe(
        "Pleated_Skirt",
        [(0.405, 0.118, 0.086), (0.385, 0.144, 0.102), (0.310, 0.184, 0.128), (0.264, 0.210, 0.144)],
        [palette["skirt"], palette["skirt_light"]], char_collection, segments=40,
        material_by_ring=[0, 0, 0], parent_bone="hips")
    skirt["AURA_part"] = "Sky pleated skirt"
    add_torus("Skirt_Waistband", (0, 0, 0.397), 0.131, 0.096, 0.012, palette["coat_light"], char_collection, "hips", segments=40, sides=8)
    add_torus("Skirt_LuminousHem", (0, 0, 0.267), 0.209, 0.142, 0.007, palette["cyan"], char_collection, "hips", segments=48, sides=8)
    for i in range(16):
        angle = 2 * math.pi * i / 16
        ca, sa = math.cos(angle), math.sin(angle)
        points = [
            (0.13 * ca, 0.098 * sa, 0.384),
            (0.169 * ca, 0.119 * sa, 0.328),
            (0.204 * ca, 0.139 * sa, 0.272),
        ]
        add_tube("Skirt_Pleat_%02d" % i, points, [0.0023, 0.002, 0.0015], palette["skirt_light"], char_collection, "hips", sides=6)
    # Tiny centered coat-tail accent at the rear hem.
    add_ellipsoid("Skirt_BackAccent", (0, 0.149, 0.29), (0.024, 0.009, 0.025), palette["cyan"], char_collection, "hips", segments=16, rings=10)


def build_neck_head(palette, char_collection):
    add_segment("Neck", (0, 0, 0.735), (0, 0, 0.835), 0.055, palette["skin"], char_collection, "neck", depth_ratio=0.9)
    # Sculpt-like oversized chibi head and softly inset ears.
    add_ellipsoid("Face_Head", (0, 0.003, 0.955), (0.214, 0.188, 0.247), palette["skin"], char_collection, "head", segments=40, rings=28)
    add_ellipsoid("Face_Nose", (0, -0.177, 0.891), (0.010, 0.006, 0.009), palette["skin_shadow"], char_collection, "head", segments=18, rings=12)
    for sign, label in ((-1, "L"), (1, "R")):
        add_ellipsoid("Ear_" + label, (sign * 0.204, -0.006, 0.943), (0.047, 0.042, 0.071), palette["skin"], char_collection, "head")
        add_ellipsoid("Ear_Inner_" + label, (sign * 0.224, -0.041, 0.947), (0.022, 0.009, 0.041), palette["skin_shadow"], char_collection, "head", segments=18, rings=12)
        # Soft blush arcs below the eyes.
        add_ellipsoid("Blush_" + label, (sign * 0.130, -0.138, 0.867), (0.030, 0.003, 0.009), palette["skin_shadow"], char_collection, "head", segments=18, rings=12)
    # Powder-blue bob cap, side buns, long tapered tails and pale highlight strands.
    add_ellipsoid("Hair_BobCap", (0, 0.020, 1.030), (0.228, 0.205, 0.225), palette["hair"], char_collection, "head", segments=36, rings=24)
    add_ellipsoid("Hair_BackBob", (0, 0.113, 0.930), (0.205, 0.115, 0.204), palette["hair_dark"], char_collection, "head", segments=32, rings=22)
    for sign, label in ((-1, "L"), (1, "R")):
        add_ellipsoid("Hair_SideBun_" + label, (sign * 0.233, 0.008, 1.040), (0.085, 0.078, 0.086), palette["hair"], char_collection, "head", segments=28, rings=18)
        add_tube("Hair_BunRidge_" + label,
                 [(sign * 0.174, -0.048, 1.087), (sign * 0.232, -0.071, 1.110), (sign * 0.285, -0.044, 1.077)],
                 [0.0035, 0.004, 0.002], palette["hair_light"], char_collection, "head", sides=7)
        add_torus("Hair_CyanTie_" + label, (sign * 0.249, 0.014, 0.977), 0.043, 0.038, 0.008, palette["cyan"], char_collection, "head", segments=22, sides=7)
        # Twin tails fall behind the shoulders; the extra fine strand gives them volume.
        tail_points = [(sign * 0.252, 0.035, 0.993), (sign * 0.305, 0.055, 0.910), (sign * 0.325, 0.075, 0.815), (sign * 0.288, 0.081, 0.735)]
        add_tube("Hair_TwinTail_" + label, tail_points, [0.065, 0.061, 0.047, 0.006], palette["hair"], char_collection, "head", sides=12)
        add_tube("Hair_TailHighlight_" + label,
                 [(sign * 0.273, -0.006, 0.946), (sign * 0.314, 0.013, 0.885), (sign * 0.309, 0.031, 0.815)],
                 [0.005, 0.004, 0.001], palette["hair_light"], char_collection, "head", sides=7)
    # Crown gloss streaks.
    add_tube("Hair_CrownGloss", [(-0.13, -0.100, 1.153), (-0.078, -0.154, 1.205), (0.004, -0.169, 1.222), (0.060, -0.146, 1.204)],
             [0.004, 0.005, 0.004, 0.001], palette["hair_light"], char_collection, "head", sides=7)
    add_tube("Hair_CrownGloss_2", [(0.079, -0.122, 1.188), (0.131, -0.080, 1.161), (0.157, -0.031, 1.115)],
             [0.003, 0.003, 0.001], palette["hair_light"], char_collection, "head", sides=7)

    # Four individually tapered locks sweep across the forehead.
    fringe_locks = [
        ((-0.173, -0.114, 1.111), (-0.186, -0.154, 1.075), (-0.139, -0.184, 1.005), (-0.120, -0.186, 0.957), 0.036, palette["hair"]),
        ((-0.105, -0.159, 1.189), (-0.094, -0.190, 1.126), (-0.062, -0.203, 1.058), (-0.041, -0.199, 0.991), 0.045, palette["hair_light"]),
        ((-0.025, -0.170, 1.211), (0.006, -0.199, 1.149), (0.012, -0.207, 1.072), (0.038, -0.195, 1.012), 0.045, palette["hair"]),
        ((0.062, -0.158, 1.186), (0.083, -0.191, 1.129), (0.104, -0.198, 1.056), (0.124, -0.182, 0.998), 0.041, palette["hair"]),
        ((0.144, -0.122, 1.133), (0.182, -0.151, 1.095), (0.181, -0.175, 1.039), (0.157, -0.179, 0.989), 0.032, palette["hair_light"]),
    ]
    for i, (p0, p1, p2, p3, width, material) in enumerate(fringe_locks):
        add_bezier_tuft("Hair_Fringe_%02d" % i, p0, p1, p2, p3, width, material, char_collection)

    # Eyes, expressive eyelids/brows and a sculpted mouth.
    eyes = {}
    for sign, label in ((-1, "Right"), (1, "Left")):
        eye = make_morphed_eye("Eye_" + label, (sign * 0.092, -0.171, 0.955), palette, char_collection, sign)
        eyes[label.lower()] = eye
    mouth = make_morphed_mouth(palette, char_collection)
    # Under-eye highlights, tiny lashes at the outside corner, and the signature star clip.
    for sign, label in ((-1, "R"), (1, "L")):
        add_tube("Face_LowerLash_" + label,
                 [(sign * 0.147, -0.184, 0.922), (sign * 0.157, -0.181, 0.913), (sign * 0.166, -0.174, 0.916)],
                 [0.0022, 0.002, 0.0008], palette["ink"], char_collection, "head", sides=6)
    # Gold star hair clip on the viewer's left, with a cyan bead.
    star_vertices = [(-0.280, -0.054, 1.090), (-0.272, -0.054, 1.108), (-0.264, -0.054, 1.090),
                     (-0.245, -0.054, 1.083), (-0.260, -0.054, 1.071), (-0.256, -0.054, 1.051),
                     (-0.272, -0.054, 1.062), (-0.288, -0.054, 1.051), (-0.284, -0.054, 1.071), (-0.299, -0.054, 1.083)]
    star = create_mesh("Hair_StarClip", star_vertices, [tuple(range(10))], [palette["gold"]], char_collection, smooth=False)
    star["AURA_parent_bone"] = "head"
    add_ellipsoid("Hair_ClipGem", (-0.272, -0.062, 1.080), (0.008, 0.004, 0.008), palette["cyan"], char_collection, "head", segments=12, rings=8)
    return eyes, mouth


def build_arms_legs(palette, char_collection):
    # Matching short sleeves and articulated little hands.
    for sign, side in ((1, "L"), (-1, "R")):
        shoulder = (sign * 0.125, 0.0, 0.716)
        elbow = (sign * 0.268, -0.005, 0.640)
        wrist = (sign * 0.365, -0.022, 0.550)
        add_ellipsoid("ShoulderCap_" + side, shoulder, (0.069, 0.073, 0.072), palette["coat"], char_collection, "upper_arm." + side)
        add_segment("UpperSleeve_" + side, shoulder, elbow, 0.057, palette["coat"], char_collection, "upper_arm." + side, depth_ratio=0.88)
        add_ellipsoid("Elbow_" + side, elbow, (0.050, 0.048, 0.051), palette["coat_shadow"], char_collection, "lower_arm." + side)
        add_segment("LowerSleeve_" + side, elbow, wrist, 0.047, palette["coat"], char_collection, "lower_arm." + side, depth_ratio=0.86)
        axis = Vector(wrist) - Vector(elbow)
        cuff_center = Vector(wrist) - axis.normalized() * 0.024
        add_torus("Sleeve_CyanCuff_" + side, cuff_center, 0.044, 0.039, 0.006, palette["cyan"], char_collection, "lower_arm." + side, segments=24, sides=7, axis=tuple(axis))
        palm = (sign * 0.382, -0.031, 0.521)
        add_ellipsoid("Hand_" + side, palm, (0.047, 0.036, 0.046), palette["skin"], char_collection, "hand." + side)
        add_segment("Thumb_" + side, (sign * 0.353, -0.040, 0.526), (sign * 0.348, -0.038, 0.500), 0.016, palette["skin"], char_collection, "hand." + side, depth_ratio=0.8)
        # Legs remain short and clear of the pleated hem.
        hip = (sign * 0.088, 0.0, 0.388)
        knee = (sign * 0.091, -0.003, 0.204)
        ankle = (sign * 0.091, -0.008, 0.092)
        add_segment("UpperLeg_" + side, hip, knee, 0.052, palette["skin"], char_collection, "upper_leg." + side, depth_ratio=0.90)
        add_ellipsoid("Knee_" + side, knee, (0.047, 0.047, 0.044), palette["skin"], char_collection, "lower_leg." + side)
        add_segment("LowerLeg_" + side, knee, ankle, 0.038, palette["skin"], char_collection, "lower_leg." + side, depth_ratio=0.88)
        sock = add_ellipsoid("Sock_" + side, (sign * 0.091, -0.013, 0.108), (0.044, 0.041, 0.062), palette["coat_light"], char_collection, "lower_leg." + side)
        add_torus("Sock_CyanBand_" + side, (sign * 0.091, -0.013, 0.132), 0.043, 0.040, 0.004, palette["cyan"], char_collection, "lower_leg." + side, segments=24, sides=7)
        add_ellipsoid("Boot_" + side, (sign * 0.091, -0.034, 0.059), (0.061, 0.086, 0.052), palette["navy"], char_collection, "foot." + side)
        add_ellipsoid("Boot_Toecap_" + side, (sign * 0.091, -0.091, 0.063), (0.051, 0.030, 0.026), palette["skirt_light"], char_collection, "foot." + side)
        add_ellipsoid("Boot_Sole_" + side, (sign * 0.091, -0.040, 0.023), (0.064, 0.090, 0.013), palette["cyan"], char_collection, "foot." + side)
        # A small star-side buckle anchors the boot design from front and back.
        add_ellipsoid("Boot_Buckle_" + side, (sign * 0.091, -0.089, 0.089), (0.011, 0.004, 0.010), palette["gold"], char_collection, "foot." + side, segments=14, rings=10)


# -----------------------------------------------------------------------------
# Rigging, VRM and export
# -----------------------------------------------------------------------------

BONE_DEFS = [
    ("hips", (0, 0, 0.365), (0, 0, 0.455), None),
    ("spine", (0, 0, 0.455), (0, 0, 0.575), "hips"),
    ("chest", (0, 0, 0.575), (0, 0, 0.710), "spine"),
    ("upperChest", (0, 0, 0.710), (0, 0, 0.755), "chest"),
    ("neck", (0, 0, 0.755), (0, 0, 0.835), "upperChest"),
    ("head", (0, 0, 0.835), (0, 0, 1.045), "neck"),
    ("leftEye", (0.092, -0.15, 0.955), (0.092, -0.22, 0.955), "head"),
    ("rightEye", (-0.092, -0.15, 0.955), (-0.092, -0.22, 0.955), "head"),
    ("leftShoulder", (0.085, 0, 0.715), (0.125, 0, 0.716), "upperChest"),
    ("leftUpperArm", (0.125, 0, 0.716), (0.268, -0.005, 0.640), "leftShoulder"),
    ("leftLowerArm", (0.268, -0.005, 0.640), (0.365, -0.022, 0.550), "leftUpperArm"),
    ("leftHand", (0.365, -0.022, 0.550), (0.405, -0.035, 0.520), "leftLowerArm"),
    ("rightShoulder", (-0.085, 0, 0.715), (-0.125, 0, 0.716), "upperChest"),
    ("rightUpperArm", (-0.125, 0, 0.716), (-0.268, -0.005, 0.640), "rightShoulder"),
    ("rightLowerArm", (-0.268, -0.005, 0.640), (-0.365, -0.022, 0.550), "rightUpperArm"),
    ("rightHand", (-0.365, -0.022, 0.550), (-0.405, -0.035, 0.520), "rightLowerArm"),
    ("leftUpperLeg", (0.088, 0, 0.388), (0.091, -0.003, 0.204), "hips"),
    ("leftLowerLeg", (0.091, -0.003, 0.204), (0.091, -0.008, 0.092), "leftUpperLeg"),
    ("leftFoot", (0.091, -0.008, 0.092), (0.091, -0.118, 0.040), "leftLowerLeg"),
    ("leftToes", (0.091, -0.118, 0.040), (0.091, -0.154, 0.038), "leftFoot"),
    ("rightUpperLeg", (-0.088, 0, 0.388), (-0.091, -0.003, 0.204), "hips"),
    ("rightLowerLeg", (-0.091, -0.003, 0.204), (-0.091, -0.008, 0.092), "rightUpperLeg"),
    ("rightFoot", (-0.091, -0.008, 0.092), (-0.091, -0.118, 0.040), "rightLowerLeg"),
    ("rightToes", (-0.091, -0.118, 0.040), (-0.091, -0.154, 0.038), "rightFoot"),
]


def create_armature(rig_collection):
    data = bpy.data.armatures.new("AURA_Humanoid_Rig")
    rig = bpy.data.objects.new("AURA_Humanoid_Rig", data)
    rig_collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = {}
    for name, head, tail, parent_name in BONE_DEFS:
        bone = data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        bone.use_deform = True
        edit_bones[name] = bone
        if parent_name:
            bone.parent = edit_bones[parent_name]
            bone.use_connect = (Vector(head) - Vector(edit_bones[parent_name].tail)).length < 0.0001
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = False
    rig.display_type = "WIRE"
    rig["AURA_Rig"] = "VRM 1.0 humanoid skeleton"
    rig["AURA_DesignReference"] = str(DESIGN_SHEET)
    return rig


def parent_rigid_parts(armature, character_collection):
    for obj in list(character_collection.objects):
        bone_name = obj.get("AURA_parent_bone")
        if not bone_name or bone_name not in armature.data.bones:
            continue
        world = obj.matrix_world.copy()
        obj.parent = armature
        obj.parent_type = "BONE"
        obj.parent_bone = bone_name
        obj.matrix_world = world
        obj["AURA_bound_to"] = bone_name


def reset_shape_key_values(character_collection):
    for obj in character_collection.objects:
        shape_keys = getattr(getattr(obj, "data", None), "shape_keys", None)
        if not shape_keys:
            continue
        for shape_key in shape_keys.key_blocks:
            if shape_key.name != "Basis":
                shape_key.value = 0.0


def configure_vrm(armature, eyes, mouth):
    extension = getattr(armature.data, "vrm_addon_extension", None)
    if extension is None:
        print("VRM add-on is not enabled. Saved Blender and GLB outputs; run this file again after enabling the official VRM add-on to export aura.vrm.")
        return False

    extension.spec_version = "1.0"
    vrm1 = extension.vrm1
    meta = vrm1.meta
    meta.vrm_name = "AURA - Desktop Assistant"
    meta.version = "1.0.0"
    meta.authors.clear()
    meta.authors.add().value = "Desktop Assistant Project"
    meta.allow_redistribution = True
    humanoid = vrm1.humanoid
    mapping = {
        "hips": "hips", "spine": "spine", "chest": "chest", "upper_chest": "upperChest",
        "neck": "neck", "head": "head", "left_eye": "leftEye", "right_eye": "rightEye",
        "left_shoulder": "leftShoulder", "left_upper_arm": "leftUpperArm", "left_lower_arm": "leftLowerArm",
        "left_hand": "leftHand", "right_shoulder": "rightShoulder", "right_upper_arm": "rightUpperArm",
        "right_lower_arm": "rightLowerArm", "right_hand": "rightHand", "left_upper_leg": "leftUpperLeg",
        "left_lower_leg": "leftLowerLeg", "left_foot": "leftFoot", "left_toes": "leftToes",
        "right_upper_leg": "rightUpperLeg", "right_lower_leg": "rightLowerLeg", "right_foot": "rightFoot",
        "right_toes": "rightToes",
    }
    for human_bone_name, blender_bone_name in mapping.items():
        human_bone = getattr(humanoid.human_bones, human_bone_name, None)
        if human_bone is not None:
            human_bone.node.bone_name = blender_bone_name

    expressions = vrm1.expressions
    preset_container = getattr(expressions, "preset", expressions)
    expression_bindings = {
        "happy": [(eyes["left"], "Happy"), (eyes["right"], "Happy"), (mouth, "Happy")],
        "angry": [(eyes["left"], "Angry"), (eyes["right"], "Angry"), (mouth, "Angry")],
        "sad": [(eyes["left"], "Sad"), (eyes["right"], "Sad"), (mouth, "Sad")],
        "surprised": [(eyes["left"], "Surprised"), (eyes["right"], "Surprised"), (mouth, "Surprised")],
        "blink": [(eyes["left"], "Blink"), (eyes["right"], "Blink")],
        "blink_left": [(eyes["left"], "BlinkLeft")],
        "blink_right": [(eyes["right"], "BlinkRight")],
        "aa": [(mouth, "Aa")], "ih": [(mouth, "Ih")], "ou": [(mouth, "Ou")],
        "ee": [(mouth, "Ee")], "oh": [(mouth, "Oh")], "relaxed": [(mouth, "Relaxed")],
    }
    for expression_name, binds in expression_bindings.items():
        expression = getattr(preset_container, expression_name, None)
        if expression is None:
            continue
        bind_collection = getattr(expression, "morph_target_binds", None)
        if bind_collection is None:
            continue
        bind_collection.clear()
        for mesh_object, shape_name in binds:
            key_blocks = mesh_object.data.shape_keys.key_blocks
            key_index = key_blocks.find(shape_name)
            if key_index < 1:
                continue
            bind = bind_collection.add()
            bind.node.mesh_object_name = mesh_object.name
            bind.index = shape_name
            bind.weight = 1.0
    print("VRM 1.0 metadata, humanoid bones, and 13 preset expressions configured")
    return True


def make_camera_and_lights(studio_collection):
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("AURA_PreviewCamera")
    camera = bpy.data.objects.new("AURA_PreviewCamera", camera_data)
    studio_collection.objects.link(camera)
    camera.location = (1.15, -3.35, 1.43)
    target = Vector((0, -0.005, 0.625))
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 1.48
    scene.camera = camera

    def area_light(name, location, power, size, color):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        studio_collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector((0, 0, 0.62)) - obj.location).to_track_quat("-Z", "Y").to_euler()
        return obj

    area_light("Key_Softbox", (1.4, -2.1, 2.55), 44, 2.0, (0.78, 0.91, 1.0))
    area_light("Fill_Softbox", (-1.8, -1.0, 1.4), 30, 1.7, (1.0, 0.78, 0.72))
    area_light("Rim_Softbox", (0.35, 1.6, 1.95), 52, 1.4, (0.55, 0.86, 1.0))
    # Collection is shown for renders but hidden in the saved modeling viewport.
    studio_collection.hide_viewport = True
    studio_collection.hide_render = False


def export_glb(armature, character_collection):
    reset_shape_key_values(character_collection)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in list(character_collection.objects):
        obj.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    result = bpy.ops.export_scene.gltf(filepath=str(GLB_PATH), export_format="GLB", use_selection=True,
                                       export_skins=True, export_morph=True, export_animations=False)
    if result != {"FINISHED"}:
        raise RuntimeError("glTF export did not finish: " + str(result))
    reset_shape_key_values(character_collection)
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    print("GLB exported to", GLB_PATH)


def export_vrm_if_enabled(configured):
    if not configured:
        return False
    operator = getattr(getattr(bpy.ops, "export_scene", None), "vrm", None)
    if operator is None:
        print("VRM export operator is unavailable")
        return False
    try:
        result = operator(filepath=str(VRM_PATH))
        if result != {"FINISHED"}:
            print("VRM export did not finish:", result)
            return False
        shutil.copy2(VRM_PATH, APP_VRM_PATH)
        print("VRM exported to", VRM_PATH)
        print("App model updated at", APP_VRM_PATH)
        return True
    except Exception as error:
        print("VRM export needs an add-on UI setup adjustment:", repr(error))
        return False


def render_preview():
    scene = bpy.context.scene
    available_engines = {item.identifier for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    if "BLENDER_EEVEE_NEXT" in available_engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in available_engines:
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = "CYCLES"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 80
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1280
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.70, 0.82, 0.92)
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.72, 0.84, 0.98, 1.0)
        background.inputs["Strength"].default_value = 0.5
    transforms = {item.identifier for item in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items}
    scene.view_settings.view_transform = "AgX" if "AgX" in transforms else "Standard"
    scene.view_settings.exposure = -0.5
    scene.render.filepath = str(PREVIEW_PATH)
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)


def build_aura():
    BLENDER_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    clear_scene()
    char_collection = new_collection("AURA Character")
    rig_collection = new_collection("AURA Humanoid Rig")
    studio_collection = new_collection("Preview Studio")
    palette = make_palette()

    build_body(palette, char_collection)
    build_arms_legs(palette, char_collection)
    eyes, mouth = build_neck_head(palette, char_collection)

    armature = create_armature(rig_collection)
    parent_rigid_parts(armature, char_collection)
    configured = configure_vrm(armature, eyes, mouth)
    reset_shape_key_values(char_collection)
    bpy.context.scene["AURA_DesignReference"] = "//aura_character_design_sheet.svg"
    bpy.context.scene["AURA_Character"] = "AURA | desktop assistant"
    bpy.context.scene["AURA_Scale"] = "1.24m stylized chibi avatar"
    if DESIGN_SHEET.exists():
        previous_reference = bpy.data.texts.get("AURA_3View_Reference.svg")
        if previous_reference:
            bpy.data.texts.remove(previous_reference)
        reference_text = bpy.data.texts.new("AURA_3View_Reference.svg")
        reference_text.from_string(DESIGN_SHEET.read_text(encoding="utf-8"))

    make_camera_and_lights(studio_collection)
    # The character collection remains the active export set; studio objects are not selected.
    export_glb(armature, char_collection)
    export_vrm_if_enabled(configured)

    # Save a useful modeling view with the full character framed and materials on.
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(False)
    bpy.context.view_layer.objects.active = None
    for area in bpy.context.screen.areas:
        if area.type == "CONSOLE":
            area.type = "VIEW_3D"
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_location = (0.0, 0.0, 0.64)
            area.spaces.active.region_3d.view_distance = 1.60
            area.spaces.active.region_3d.view_perspective = "ORTHO"
            area.spaces.active.region_3d.view_rotation = (0.70710678, 0.70710678, 0.0, 0.0)
            area.spaces.active.overlay.show_bones = True
            area.spaces.active.shading.type = "MATERIAL"
    render_preview()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print("AURA build complete:", BLEND_PATH, GLB_PATH, PREVIEW_PATH)


if __name__ == "__main__":
    build_aura()
