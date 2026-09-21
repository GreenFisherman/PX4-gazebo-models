#!/usr/bin/env python3
"""Regression against the supplied QGC screenshot, not just the Gazebo mesh.

The orange vertices in docs/gravenbol_boundary_off.png are known GPS points.
Their fitted north-up map projection puts (51.971659, 5.384925) at
(1313.956, 587.691), at approximately 2.026 pixels/metre. The old fence
crossed the eastern peninsula; checking only against its own mesh missed it.
"""
import math
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'models/gravenbol'))
import geofence


def screenshot_point(latitude, longitude):
    lat = math.radians(51.971659)
    a, e2 = 6378137, 6.6943799901413165e-3
    n = a / math.sqrt(1-e2*math.sin(lat)**2)
    m = a*(1-e2)/(1-e2*math.sin(lat)**2)**1.5
    east = math.radians(longitude-5.384925)*n*math.cos(lat)
    north = math.radians(latitude-51.971659)*m
    return 1313.956 + 2.024*east, 587.691 - 2.028*north


class MapAlignmentTest(unittest.TestCase):
    def test_fence_fits_visible_main_basin(self):
        world = ET.parse(ROOT / 'worlds/fish_usv.sdf').getroot().find('world')
        origin = tuple(float(world.findtext('spherical_coordinates/'+name))
                       for name in ('latitude_deg', 'longitude_deg', 'elevation'))
        points = [screenshot_point(*geofence.global_coordinates(x, y, *origin))
                  for x, y in geofence.FENCE]
        # Independent, easily recognizable extents in the reference screenshot.
        # East of x=1400 is beach/peninsula; south of y=850 is dry land.
        self.assertLess(max(x for x, y in points), 1380,
                        'Fence extends across the eastern beach/peninsula in QGC')
        self.assertGreater(max(x for x, y in points), 1300)
        self.assertLess(max(y for x, y in points), 825)
        self.assertLess(min(x for x, y in points), 130)
        self.assertGreater(min(x for x, y in points), 45)


if __name__ == '__main__':
    unittest.main()
