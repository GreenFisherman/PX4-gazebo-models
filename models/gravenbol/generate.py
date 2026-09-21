#!/usr/bin/env python3
"""Generate Gravenbol terrain from docs/gravenbol_boundary_off.png.

No external assets or Python dependencies are required. Coordinates below are
image pixels, not surveyed geographic points. See README.md for assumptions.
"""

import math
from pathlib import Path
import random
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
# Reference: docs/gravenbol_boundary_off.png (2048 x 1030, north up).
# The old fence's known WGS84 vertices calibrate this screenshot. A least-
# squares fit of its orange vertices locates the existing GPS origin beside
# the eastern beach, NOT at the central marker in the earlier image.
# Separate scales account for the local WGS84 east/north map projection.
PIXELS_PER_METRE = (2.024, 2.028)
ORIGIN_PIXEL = (1313.956, 587.691)  # 51.971659 N, 5.384925 E
SHORE_PIXELS = [
    (18, 217), (55, 180), (102, 155), (166, 144), (200, 106),
    (240, 98), (295, 108), (365, 136), (430, 166), (495, 180),
    (557, 186), (618, 183), (658, 148), (666, 97), (691, 64),
    (713, 34), (722, -25), (1035, -25),
    # Cap the cropped inlet, then follow the lake side of the hooked spit.
    (1025, 64), (1042, 119), (1025, 150), (1020, 194),
    (1026, 252), (1044, 309), (1075, 348), (1150, 363),
    (1211, 368), (1260, 390), (1310, 414), (1350, 445),
    # Water's edge of the eastern beach, not the grass/sand boundary.
    (1380, 486), (1388, 540), (1389, 593), (1371, 633),
    (1340, 656), (1290, 670), (1244, 694), (1190, 724),
    (1125, 752), (1052, 778), (979, 799), (900, 810),
    (820, 823), (735, 833), (650, 842), (550, 844),
    (430, 836), (300, 835), (190, 825), (95, 808),
    (58, 765), (59, 691), (49, 617), (39, 550),
    (38, 478), (29, 400), (19, 331), (20, 271),
]
GRID_STEP = 4.0


def local(pixel):
    return ((pixel[0] - ORIGIN_PIXEL[0]) / PIXELS_PER_METRE[0],
            (ORIGIN_PIXEL[1] - pixel[1]) / PIXELS_PER_METRE[1])


SHORE = [local(p) for p in SHORE_PIXELS]


def shore_distance(x, y):
    """Signed distance to shoreline in metres: positive on land."""
    inside = False
    nearest = float('inf')
    for a, b in zip(SHORE, SHORE[1:] + SHORE[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0.0, min(1.0, ((x-a[0])*dx + (y-a[1])*dy) / (dx*dx+dy*dy)))
        nearest = min(nearest, math.hypot(x-a[0]-t*dx, y-a[1]-t*dy))
        if (a[1] > y) != (b[1] > y):
            if x < a[0] + (y-a[1])*dx/dy:
                inside = not inside
    return -nearest if inside else nearest


def terrain_height(x, y, distance=None):
    d = shore_distance(x, y) if distance is None else distance
    ripple = math.sin(x*.17 + math.sin(y*.12)) * math.cos(y*.21) * .18
    if d < 0:
        # Approximate 1:4 underwater slope to a 5 m basin, not bathymetry.
        return -min(5.0, -d/4) + ripple * min(1.0, -d/25)
    return min(1.8, d*.18) + ripple * min(1.0, d/15)


def add(parent, tag, text=None, **attributes):
    node = ET.SubElement(parent, tag, attributes)
    if text is not None:
        node.text = str(text)
    return node


def write_xml(path, root):
    ET.indent(root, space='  ')
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def mesh_geometry(parent):
    add(add(add(parent, 'geometry'), 'mesh'), 'uri', 'model://gravenbol/meshes/terrain.dae')


def generate_mesh():
    # Extra land margin around the screenshot. Mesh axes are ENU / Z-up.
    xmin, ymax = local((-80, -120))
    xmax, ymin = local((1570, 1000))
    nx = math.ceil((xmax-xmin) / GRID_STEP)
    ny = math.ceil((ymax-ymin) / GRID_STEP)
    vertices = []
    distances = []
    for j in range(ny+1):
        for i in range(nx+1):
            x, y = xmin + i*GRID_STEP, ymin + j*GRID_STEP
            d = shore_distance(x, y)
            vertices.append((x, y, terrain_height(x, y, d)))
            distances.append(d)
    faces = [[] for _ in range(18)]
    for j in range(ny):
        for i in range(nx):
            a = j*(nx+1)+i
            for tri in ((a, a+1, a+nx+2), (a, a+nx+2, a+nx+1)):
                x, y, z = (sum(vertices[k][axis] for k in tri)/3 for axis in range(3))
                d = sum(distances[k] for k in tri)/3
                family = 0 if d < -8 else 1 if d < 7 else 2
                pattern = (math.sin(x*.19 + math.sin(y*.31)) + math.cos(y*.15+x*.09)) / 4 + .5
                shade = min(5, int(pattern*6))
                faces[family*6+shade].extend(tri)

    root = ET.Element('COLLADA', xmlns='http://www.collada.org/2005/11/COLLADASchema', version='1.4.1')
    asset = add(root, 'asset')
    add(asset, 'created', '2026-09-12T00:00:00Z')
    add(asset, 'modified', '2026-09-12T00:00:00Z')
    add(asset, 'unit', name='meter', meter='1')
    add(asset, 'up_axis', 'Z_UP')
    effects, materials = add(root, 'library_effects'), add(root, 'library_materials')
    for k in range(18):
        base = ((.42, .36, .23), (.63, .55, .37), (.19, .32, .12))[k//6]
        gain = .83 + (k % 6)*.065
        color = ' '.join(f'{v*gain:.3f}' for v in base) + ' 1'
        effect = add(effects, 'effect', id=f'effect{k}')
        phong = add(add(add(effect, 'profile_COMMON'), 'technique', sid='common'), 'phong')
        for tag in ('ambient', 'diffuse'):
            add(add(phong, tag), 'color', color)
        material = add(materials, 'material', id=f'material{k}', name=f'material{k}')
        add(material, 'instance_effect', url=f'#effect{k}')
    mesh = add(add(add(root, 'library_geometries'), 'geometry', id='terrain'), 'mesh')
    source = add(mesh, 'source', id='positions')
    add(source, 'float_array', ' '.join(f'{v:.4f}' for p in vertices for v in p),
        id='positions-array', count=str(len(vertices)*3))
    accessor = add(add(source, 'technique_common'), 'accessor', source='#positions-array', count=str(len(vertices)), stride='3')
    for axis in 'XYZ':
        add(accessor, 'param', name=axis, type='float')
    # Gazebo's DART mesh collision loader requires a normal for every vertex.
    normals = []
    for j in range(ny+1):
        for i in range(nx+1):
            left, right = max(0, i-1), min(nx, i+1)
            down, up = max(0, j-1), min(ny, j+1)
            dzdx = (vertices[j*(nx+1)+right][2] - vertices[j*(nx+1)+left][2]) / ((right-left)*GRID_STEP)
            dzdy = (vertices[up*(nx+1)+i][2] - vertices[down*(nx+1)+i][2]) / ((up-down)*GRID_STEP)
            length = math.sqrt(dzdx*dzdx + dzdy*dzdy + 1)
            normals.extend((-dzdx/length, -dzdy/length, 1/length))
    source = add(mesh, 'source', id='normals')
    add(source, 'float_array', ' '.join(f'{v:.6f}' for v in normals), id='normals-array', count=str(len(normals)))
    accessor = add(add(source, 'technique_common'), 'accessor', source='#normals-array', count=str(len(vertices)), stride='3')
    for axis in 'XYZ':
        add(accessor, 'param', name=axis, type='float')
    add(add(mesh, 'vertices', id='vertices'), 'input', semantic='POSITION', source='#positions')
    for k, indices in enumerate(faces):
        triangles = add(mesh, 'triangles', count=str(len(indices)//3), material=f'material{k}')
        add(triangles, 'input', semantic='VERTEX', source='#vertices', offset='0')
        add(triangles, 'input', semantic='NORMAL', source='#normals', offset='1')
        add(triangles, 'p', ' '.join(f'{i} {i}' for i in indices))
    scene = add(add(root, 'library_visual_scenes'), 'visual_scene', id='scene')
    instance = add(add(scene, 'node', id='terrain-node'), 'instance_geometry', url='#terrain')
    bindings = add(add(instance, 'bind_material'), 'technique_common')
    for k in range(18):
        add(bindings, 'instance_material', symbol=f'material{k}', target=f'#material{k}')
    add(add(root, 'scene'), 'instance_visual_scene', url='#scene')
    (HERE / 'meshes').mkdir(exist_ok=True)
    write_xml(HERE / 'meshes/terrain.dae', root)
    return xmin, ymin, nx*GRID_STEP, ny*GRID_STEP, len(vertices)


def sphere(parent, name, xyz, scale, color):
    visual = add(parent, 'visual', name=name)
    add(visual, 'pose', f'{xyz[0]:.3f} {xyz[1]:.3f} {xyz[2]:.3f} 0 0 0')
    add(add(add(visual, 'geometry'), 'ellipsoid'), 'radii', ' '.join(map(str, scale)))
    mat = add(visual, 'material')
    add(mat, 'ambient', color)
    add(mat, 'diffuse', color)


def generate_model(bounds):
    xmin, ymin, width, height, _ = bounds
    root = ET.Element('sdf', version='1.9')
    model = add(root, 'model', name='gravenbol')
    add(model, 'static', 'true')
    terrain = add(model, 'link', name='terrain')
    mesh_geometry(add(terrain, 'collision', name='solid_banks_and_lakebed'))
    mesh_geometry(add(terrain, 'visual', name='grass_sand_and_sediment'))
    water = add(model, 'link', name='water')
    # Land rises above this visual plane; there is deliberately no water collision.
    add(water, 'pose', f'{xmin+width/2:.3f} {ymin+height/2:.3f} 0 0 0 0')
    visual = add(water, 'visual', name='surface')
    plane = add(add(visual, 'geometry'), 'plane')
    add(plane, 'normal', '0 0 1')
    add(plane, 'size', f'{width:.3f} {height:.3f}')
    add(visual, 'transparency', '.48')
    add(visual, 'cast_shadows', 'false')
    material = add(visual, 'material')
    add(material, 'ambient', '.06 .25 .28 1')
    add(material, 'diffuse', '.08 .32 .35 1')
    rng = random.Random(1610)
    trees = add(model, 'link', name='shoreline_trees')
    positions = []
    for _ in range(12000):
        if len(positions) >= 110:
            break
        x, y = rng.uniform(xmin, xmin+width), rng.uniform(ymin, ymin+height)
        d = shore_distance(x, y)
        if not 9 < d < 40 or any(math.hypot(x-a, y-b) < 9 for a, b in positions):
            continue
        positions.append((x, y))
        z, h = terrain_height(x, y, d), rng.uniform(4, 7)
        index = len(positions)
        for tag in ('visual', 'collision'):
            trunk = add(trees, tag, name=f'trunk_{index}_{tag}')
            add(trunk, 'pose', f'{x:.3f} {y:.3f} {z+h/2:.3f} 0 0 0')
            cylinder = add(add(trunk, 'geometry'), 'cylinder')
            add(cylinder, 'radius', '.23')
            add(cylinder, 'length', f'{h:.3f}')
            if tag == 'visual':
                mat = add(trunk, 'material')
                add(mat, 'ambient', '.24 .17 .10 1')
                add(mat, 'diffuse', '.24 .17 .10 1')
        sphere(trees, f'crown_{index}', (x, y, z+h), (2.7, 2.7, 3.3), '.12 .27 .09 1')
    rocks = add(model, 'link', name='underwater_stones')
    for i in range(65):
        x, y = rng.uniform(-70, 70), rng.uniform(-70, 70)
        if shore_distance(x, y) > -15:
            continue
        radius = rng.uniform(.15, .5)
        sphere(rocks, f'stone_{i}', (x, y, terrain_height(x, y)),
               (radius, radius*.8, radius*.5), '.32 .30 .25 1')
    write_xml(HERE / 'model.sdf', root)


def main():
    bounds = generate_mesh()
    generate_model(bounds)
    print(f'Scale (east/north): {PIXELS_PER_METRE} pixels/m; terrain: {bounds[2]:.0f} x {bounds[3]:.0f} m; {bounds[4]} vertices')
    print(f'Origin lakebed: {terrain_height(0, 0):.2f} m; shore clearance: {-shore_distance(0, 0):.1f} m')


if __name__ == '__main__':
    main()
