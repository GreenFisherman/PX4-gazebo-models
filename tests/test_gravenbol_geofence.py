#!/usr/bin/env python3
"""Geometry and coordinate tests for the automatically loaded lake fence."""

import math
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'models/gravenbol'))
import geofence
from generate import local, shore_distance, SHORE


class GeofenceTest(unittest.TestCase):
    def test_margin_and_inlet(self):
        self.assertGreaterEqual(geofence.validate_boundary(), 23)
        self.assertTrue(geofence.contains(0, 0))
        self.assertFalse(geofence.contains(*local((880, 20))))
        self.assertFalse(geofence.contains(*local((-30, 450))))

    def test_entire_allowed_region_is_water(self):
        # Also check the interior; concave shoreline pockets must not be enclosed.
        for x in range(math.floor(min(p[0] for p in SHORE)), math.ceil(max(p[0] for p in SHORE)), 4):
            for y in range(math.floor(min(p[1] for p in SHORE)), math.ceil(max(p[1] for p in SHORE)), 4):
                if geofence.contains(x, y):
                    self.assertLessEqual(shore_distance(x, y), -20)

    def test_no_crossing_edges(self):
        def side(a, b, c):
            return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        edges = list(zip(geofence.FENCE, geofence.FENCE[1:]+geofence.FENCE[:1]))
        for i, (a, b) in enumerate(edges):
            for j, (c, d) in enumerate(edges):
                if j <= i+1 or (i == 0 and j == len(edges)-1):
                    continue
                self.assertFalse(side(a, b, c)*side(a, b, d) < 0 and side(c, d, a)*side(c, d, b) < 0)

    def test_geographic_origin_and_axes(self):
        for lat, lon, alt in ((51.971659, 5.384925, 0), (-35, 140, 500)):
            result = geofence.global_coordinates(0, 0, lat, lon, alt)
            self.assertAlmostEqual(result[0], lat, places=8)
            self.assertAlmostEqual(result[1], lon, places=8)
            self.assertGreater(geofence.global_coordinates(100, 0, lat, lon, alt)[1], lon)
            self.assertGreater(geofence.global_coordinates(0, 100, lat, lon, alt)[0], lat)

    def test_world_origin_and_relocation(self):
        root = ET.parse(ROOT / 'worlds/fish_usv.sdf').getroot()
        self.assertEqual(geofence.parse_world_origin(ET.tostring(root), 'fish_usv'), (51.971659, 5.384925, 0))
        root.find('world/spherical_coordinates/latitude_deg').text = '52'
        self.assertEqual(geofence.parse_world_origin(ET.tostring(root), 'fish_usv')[0], 52)
        ET.SubElement(root.find('world/include'), 'pose').text = '20 0 0 0 0 0'
        with self.assertRaises(ValueError):
            geofence.parse_world_origin(ET.tostring(root), 'fish_usv')

    def test_acknowledged_origin_override(self):
        original = (51.971659, 5.384925, 0)
        self.assertEqual(geofence.origin_override(original, {}), original)
        self.assertEqual(geofence.origin_override(original, {
            'PX4_HOME_LAT': '52', 'PX4_HOME_LON': '6', 'PX4_HOME_ALT': '10'}), (52, 6, 10))
        for values in ({'PX4_HOME_LAT': '52'},
                       {'PX4_HOME_LAT': 'nan', 'PX4_HOME_LON': '6', 'PX4_HOME_ALT': '0'}):
            with self.assertRaises(ValueError):
                geofence.origin_override(original, values)

    def test_file_format_and_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fence.txt'
            for origin in ((51.971659, 5.384925, 0), (52, 6, 10)):
                geofence.write_fence(path, *origin)
                lines = [line for line in path.read_text().splitlines() if not line.startswith('#')]
                self.assertEqual(len(lines), len(geofence.FENCE)+1)
                for line, (x, y) in zip(lines[1:], geofence.FENCE):
                    actual = [float(value) for value in line.split()]
                    expected = geofence.global_coordinates(x, y, *origin)
                    for a, b in zip(actual, expected):
                        self.assertTrue(math.isfinite(a))
                        self.assertAlmostEqual(a, b, places=8)
                self.assertFalse(path.with_suffix('.tmp').exists())


if __name__ == '__main__':
    unittest.main()
