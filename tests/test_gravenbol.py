#!/usr/bin/env python3
"""Dependency-free geometry / launch integration checks for the lake model."""

import importlib.util
import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('gravenbol', ROOT / 'models/gravenbol/generate.py')
LAKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAKE)


class GravenbolTest(unittest.TestCase):
    def test_calibrated_map_scale(self):
        # QGC screenshot calibration, independent of the discarded central anchor.
        a, b = LAKE.local((100, 600)), LAKE.local((1100, 600))
        self.assertAlmostEqual(math.dist(a, b), 1000 / 2.024)
        self.assertAlmostEqual(LAKE.local((1313.956, 384.891))[1], 100)

    def test_spawn_and_banks(self):
        self.assertEqual(LAKE.local(LAKE.ORIGIN_PIXEL), (0, 0))
        self.assertLess(LAKE.shore_distance(0, 0), -30)
        self.assertGreater(LAKE.shore_distance(0, 0), -40)
        self.assertAlmostEqual(LAKE.terrain_height(0, 0), -5)
        self.assertGreater(LAKE.terrain_height(*LAKE.local((-30, 450))), 1)
        # Northeastern spit stays land, unlike a rectangular pond.
        self.assertGreater(LAKE.terrain_height(*LAKE.local((1200, 280))), 0)
        for point in LAKE.SHORE:
            self.assertAlmostEqual(LAKE.terrain_height(*point), 0, places=6)

    def test_worlds_share_terrain_and_gps(self):
        for name in ('worlds/fish_usv.sdf', 'models/fish_usv/demo.sdf'):
            world = ET.parse(ROOT / name).getroot().find('world')
            self.assertIn('model://gravenbol', [x.text for x in world.findall('include/uri')])
            self.assertIsNone(world.find("model[@name='seabed']"))
            coordinates = world.find('spherical_coordinates')
            self.assertEqual(float(coordinates.findtext('latitude_deg')), 51.971659)
            self.assertEqual(float(coordinates.findtext('longitude_deg')), 5.384925)

    def test_beach_launch_faces_into_lake(self):
        demo = ET.parse(ROOT / 'models/fish_usv/demo.sdf').getroot().find('world')
        boat = next(item for item in demo.findall('include') if item.findtext('uri') == 'model://fish_usv')
        pose = list(map(float, boat.findtext('pose').split()))
        self.assertEqual(pose[:5], [0, 0, .131, 0, 0])
        self.assertAlmostEqual(pose[5], math.pi)
        airframe = ROOT.parents[2] / 'ROMFS/px4fmu_common/init.d-posix/airframes/22001_gz_fish_usv'
        self.assertIn('0,0,0.131,0,0,3.141592653589793', airframe.read_text())

    def test_collision_matches_visual(self):
        root = ET.parse(ROOT / 'models/gravenbol/model.sdf').getroot()
        terrain = root.find("model/link[@name='terrain']")
        self.assertEqual(terrain.findtext('collision/geometry/mesh/uri'),
                         terrain.findtext('visual/geometry/mesh/uri'))
        self.assertEqual(root.findtext('model/static'), 'true')
        self.assertIsNone(root.find("model/link[@name='water']/collision"))

    def test_mesh_is_finite_and_faces_up(self):
        ns = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
        root = ET.parse(ROOT / 'models/gravenbol/meshes/terrain.dae').getroot()
        array = root.find('.//c:float_array', ns)
        floats = [float(v) for v in array.text.split()]
        self.assertTrue(all(math.isfinite(v) for v in floats))
        self.assertEqual(int(array.attrib['count']), len(floats))
        vertices = list(zip(floats[::3], floats[1::3], floats[2::3]))
        # A shared map/fence fix must regenerate the actual collision mesh too.
        for x, y, z in vertices[::137]:
            self.assertAlmostEqual(z, LAKE.terrain_height(x, y), delta=.0001)
        normals = [float(v) for v in root.find(".//c:float_array[@id='normals-array']", ns).text.split()]
        self.assertEqual(len(normals), len(floats))
        for i in range(0, len(normals), 3):
            self.assertAlmostEqual(sum(v*v for v in normals[i:i+3]), 1, places=5)
        count = 0
        for group in root.findall('.//c:triangles', ns):
            pairs = [int(v) for v in group.find('c:p', ns).text.split()]
            self.assertEqual(pairs[::2], pairs[1::2])
            indices = pairs[::2]
            self.assertEqual(len(indices), int(group.attrib['count'])*3)
            for i in range(0, len(indices), 3):
                a, b, c = (vertices[k] for k in indices[i:i+3])
                cross_z = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                self.assertGreater(cross_z, 0)
                count += 1
        self.assertGreater(count, 50000)


if __name__ == '__main__':
    unittest.main()
