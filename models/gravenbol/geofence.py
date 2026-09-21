#!/usr/bin/env python3
"""Produce an instance-local PX4 inclusion fence for the Gravenbol main basin.

The deliberately conservative polygon excludes the narrow northern inlet.
No Python dependencies beyond the standard library are needed.
"""

import argparse
import ast
import math
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from generate import local, shore_distance


SAFETY_MARGIN = 20.0
# Kept in the same image coordinate system as the traced shoreline. These
# hand-selected inset vertices avoid concave corners and shallow narrow areas.
FENCE_PIXELS = [
    (85, 250), (130, 220), (240, 164), (350, 193), (480, 240),
    (625, 246), (712, 182), (760, 95), (945, 90), (969, 180),
    (981, 302), (1038, 391), (1185, 420), (1270, 462),
    (1320, 510), (1338, 562), (1320, 600), (1250, 625),
    (1150, 687), (990, 741), (815, 770), (650, 789),
    (430, 783), (210, 772), (112, 738), (99, 575), (84, 415),
]
FENCE = [local(p) for p in FENCE_PIXELS]


def contains(x, y):
    inside = False
    for a, b in zip(FENCE, FENCE[1:] + FENCE[:1]):
        if (a[1] > y) != (b[1] > y):
            if x < a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1]):
                inside = not inside
    return inside


def validate_boundary():
    """Check every edge, not only vertices, against the concave shoreline."""
    minimum = float('inf')
    for a, b in zip(FENCE, FENCE[1:] + FENCE[:1]):
        count = math.ceil(math.dist(a, b)*2)  # samples at most 0.5 m apart
        for i in range(count+1):
            x, y = (a[j] + (b[j]-a[j])*i/count for j in range(2))
            minimum = min(minimum, -shore_distance(x, y))
    # An extra 3 m accounts for interpolation and the terrain's 4 m grid.
    if minimum < SAFETY_MARGIN + 3 or not contains(0, 0):
        raise ValueError(f'Unsafe boundary: minimum traced shore clearance {minimum:.2f} m')
    return minimum


def global_coordinates(east, north, latitude, longitude, elevation=0):
    """WGS84 local tangent plane (ENU) to geodetic coordinates."""
    a, e2 = 6378137.0, 6.6943799901413165e-3
    lat, lon = math.radians(latitude), math.radians(longitude)
    n = a / math.sqrt(1-e2*math.sin(lat)**2)
    x = (n+elevation)*math.cos(lat)*math.cos(lon) - east*math.sin(lon) - north*math.sin(lat)*math.cos(lon)
    y = (n+elevation)*math.cos(lat)*math.sin(lon) + east*math.cos(lon) - north*math.sin(lat)*math.sin(lon)
    z = (n*(1-e2)+elevation)*math.sin(lat) + north*math.cos(lat)
    p = math.hypot(x, y)
    result_lat = math.atan2(z, p*(1-e2))
    for _ in range(6):
        n = a/math.sqrt(1-e2*math.sin(result_lat)**2)
        result_lat = math.atan2(z+e2*n*math.sin(result_lat), p)
    return math.degrees(result_lat), math.degrees(math.atan2(y, x))


def parse_world_origin(sdf, world):
    exported = ET.fromstring(sdf).find('world')
    if exported is None or exported.get('name') != world:
        raise ValueError('Gazebo returned a different world')
    terrain = next((item for item in exported.findall('include')
                    if (item.findtext('uri') or '').rstrip('/').endswith('/gravenbol')), None)
    if terrain is None:
        terrain = exported.find("model[@name='gravenbol']")
    if terrain is None:
        raise ValueError('World does not contain the Gravenbol terrain')
    pose = [float(v) for v in terrain.findtext('pose', '0 0 0 0 0 0').split()]
    if len(pose) != 6 or any(not math.isfinite(v) or abs(v) > 1e-6 for v in pose):
        raise ValueError('The fence requires Gravenbol terrain at the world origin')
    coords = exported.find('spherical_coordinates')
    if coords is None or coords.findtext('surface_model') != 'EARTH_WGS84':
        raise ValueError('Only WGS84 worlds are supported')
    lat, lon, alt = (float(coords.findtext(name, '0')) for name in ('latitude_deg', 'longitude_deg', 'elevation'))
    if not all(math.isfinite(v) for v in (lat, lon, alt)) or abs(lat) >= 89 or abs(lon) > 180:
        raise ValueError('Invalid or unsupported world origin')
    heading = float(coords.findtext('heading_deg', '0'))
    if not math.isfinite(heading) or abs(heading) > 1e-6 or coords.findtext('world_frame_orientation', 'ENU') != 'ENU':
        raise ValueError('The Gravenbol fence requires the default ENU heading')
    return lat, lon, alt


def origin_override(origin, environment):
    names = ('PX4_HOME_LAT', 'PX4_HOME_LON', 'PX4_HOME_ALT')
    if any(environment.get(name) for name in names):
        if not all(environment.get(name) for name in names):
            raise ValueError('All three PX4_HOME_* values must be set together')
        origin = tuple(float(environment[name]) for name in names)
        if not all(math.isfinite(v) for v in origin) or abs(origin[0]) >= 89 or abs(origin[1]) > 180:
            raise ValueError('Invalid PX4_HOME_* origin override')
    return origin


def world_origin(world):
    if world not in ('fish_usv', 'fish_usv_demo'):
        raise ValueError('The Gravenbol fence is only defined for fish_usv / fish_usv_demo worlds')
    # Harmonic has no spherical-coordinate getter. Its world export retains
    # the SDF's original coordinates even after set_spherical_coordinates.
    # Validate the terrain layout, then honour the acknowledged startup override.
    response = subprocess.run([
        'gz', 'service', '-s', f'/world/{world}/generate_world_sdf',
        '--reqtype', 'gz.msgs.SdfGeneratorConfig', '--reptype', 'gz.msgs.StringMsg',
        '--timeout', '5000', '--req', '',
    ], check=True, capture_output=True, text=True, timeout=10)
    if not response.stdout.startswith('data: '):
        raise ValueError('No valid world export response from Gazebo')
    sdf = ast.literal_eval(response.stdout[6:].strip())
    return origin_override(parse_world_origin(sdf, world), os.environ)


def write_fence(output, latitude, longitude, elevation):
    minimum = validate_boundary()
    lines = ['# Gravenbol main-basin inclusion fence; regenerated at fish_usv startup.',
             '# At least 20 m inside the modeled shore; northern inlet excluded.',
             '-10000 100000']
    for east, north in FENCE:
        lat, lon = global_coordinates(east, north, latitude, longitude, elevation)
        lines.append(f'{lat:.10f} {lon:.10f}')
    # Replace only this generated instance-local file, never the user's SD-card fence.
    output = Path(output)
    temporary = output.with_suffix('.tmp')
    temporary.write_text('\n'.join(lines) + '\n')
    temporary.replace(output)
    print(f'Gravenbol fence: {len(FENCE)} vertices, {minimum:.1f} m minimum traced clearance; origin {latitude}, {longitude}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    write_fence(args.output, *world_origin(args.world))


if __name__ == '__main__':
    main()
