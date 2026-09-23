#!/usr/bin/env python3
"""Checks the Fish USV camera GUI configuration."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class CameraConfigTest(unittest.TestCase):
    def test_gui_config_contains_both_camera_displays(self):
        gui = ET.parse(ROOT / 'models/fish_usv/camera.config').getroot()
        self.assertEqual(gui.tag, 'gui')

        topics = [plugin.findtext('topic') for plugin in gui.findall('plugin')]
        self.assertEqual(topics, [
            '/world/fish_usv/model/fish_usv_0/link/base_link/sensor/fish_camera/image',
            '/world/fish_usv/model/fish_usv_0/link/base_link/sensor/forward_camera/image',
        ])


if __name__ == '__main__':
    unittest.main()
