#!/usr/bin/env python3
"""Write a vector alignment overlay beside gravenbol_boundary_off.png."""
import argparse
import xml.etree.ElementTree as ET

from generate import ORIGIN_PIXEL, SHORE_PIXELS
from geofence import FENCE_PIXELS, validate_boundary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', help='SVG path, beside the reference PNG in docs/')
    args = parser.parse_args()
    validate_boundary()
    root = ET.Element('svg', xmlns='http://www.w3.org/2000/svg',
                      viewBox='0 0 2048 1030', width='2048', height='1030')
    ET.SubElement(root, 'image', href='gravenbol_boundary_off.png', width='2048', height='1030')
    for points, color, width in ((SHORE_PIXELS, '#ffffff', '2'), (FENCE_PIXELS, '#00ffb0', '5')):
        ET.SubElement(root, 'polygon', points=' '.join(f'{x},{y}' for x, y in points),
                      fill='none', stroke=color, **{'stroke-width': width})
    x, y = ORIGIN_PIXEL
    ET.SubElement(root, 'circle', cx=str(x), cy=str(y), r='12', fill='#00cfff', stroke='white',
                  **{'stroke-width': '3'})
    ET.SubElement(root, 'path', d=f'M {x-15} {y} h -55 l 15 -10 m -15 10 l 15 10',
                  fill='none', stroke='#00cfff', **{'stroke-width': '4'})
    ET.SubElement(root, 'rect', x='30', y='905', width='890', height='100', rx='8', fill='#102030', opacity='.95')
    for yy, label, color in (
        (932, 'GREEN: corrected 27-point fence | WHITE: traced waterline', '#00ffb0'),
        (961, 'BLUE: beach-side home, afloat, facing west | ORANGE: old incorrect fence', '#00cfff'),
        (990, 'Screenshot-aligned approximation, not a surveyed navigation boundary', '#ffffff'),
    ):
        ET.SubElement(root, 'text', x='45', y=str(yy), fill=color,
                      **{'font-family': 'sans-serif', 'font-size': '21'}).text = label
    ET.indent(root)
    ET.ElementTree(root).write(args.output, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    main()
