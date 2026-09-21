# Gravenbol lake approximation

This local, dependency-free model is traced from the user-supplied
`docs/gravenbol_boundary_off.png` in the PX4 repository. It is included by both the
`fish_usv` PX4 world and `fish_usv_demo` standalone world.

## Scale and alignment

The original `docs/gravenbol.png` supplied an approximate scale using its
cumulative 1.61 km measurement. However, assigning the GPS coordinates to its
central blue marker was wrong: the QGC screenshot shows that those coordinates
are beside the eastern beach. This shifted the original fence onto land.

The replacement uses the clearer, north-up 2048 x 1030 QGC screenshot as its
coordinate reference. The old orange fence is useful as a calibration grid:
its 24 vertices have known ENU/GPS positions. Fitting those vertices to the
screenshot gives 2.024 east and 2.028 north pixels/metre and puts
51.971659 N, 5.384925 E at pixel (1313.956, 587.691). The fit residual is about
2.3 pixels at worst (roughly 1.2 m); shoreline tracing and imagery add further
uncertainty. The main basin is roughly 680 m east-west.

`generate.py` traces the water's edge in this reference, including the lake
side of the eastern beach, and uses the same pixel-to-ENU transform as the
fence. Local (0, 0) is now the eastern beach launch area, approximately 35 m
offshore, not lake centre. Both launch modes face west into open water. The
boat is deliberately afloat, not placed on the dry beach or outside its
20 m safety margin. PX4 sets home at this spawn position.

This is screenshot registration, not surveyed GIS alignment. A changed map
image, seasonal waterline or GPS origin override may not match the reference.

## Geometry and limitations

- A 4 m terrain mesh supplies both visible ground and static collisions.
- The western bank, curved southern bank, eastern beach and northeastern
  hooked spit follow the visible shoreline; the northern inlet is capped
  just beyond the image edge. The river beyond the crop is not reconstructed.
- Water is at local Z=0. The bed slopes at approximately 1:4 from the traced
  shoreline to a roughly 5 m central depth, with small synthetic undulations.
  Land rises to approximately 1.8 m. These elevations are assumptions:
  neither bathymetry nor surveyed water elevation was provided.
- Grass, sand and sediment use procedural material patches, not aerial-photo
  textures. Tree placement and underwater stones are illustrative, not traced.
  Tree trunks collide; crowns and small stones are visual-only.
- Freshwater buoyancy remains in the enclosing worlds. The water surface is
  visual-only, so the boat floats instead of sitting on a solid water plane.
- No real waves, currents, water optics, fish or detection labels are added.
  This is suitable for approximate route/camera experiments, not validating
  real-world navigation clearance or sonar performance.

Regenerate the checked-in local assets after editing the outline or assumptions:

```bash
python3 Tools/simulation/gz/models/gravenbol/generate.py
```

Restart Gazebo after regeneration. No Fuel downloads or extra Python packages
are required.

For a visual comparison against the QGC screenshot, open
`docs/gravenbol_alignment.svg` in a browser. Green is the corrected fence,
white the traced shore and blue the beach-side launch; orange is the old
incorrect fence already present in the screenshot. Keep the SVG alongside
the reference PNG. Regenerate the overlay with:

```bash
python3 Tools/simulation/gz/models/gravenbol/preview.py docs/gravenbol_alignment.svg
```

## Validation

Run these checks from the PX4 root:

```bash
python3 Tools/simulation/gz/tests/test_gravenbol.py
python3 Tools/simulation/gz/tests/test_gravenbol_geofence.py
python3 Tools/simulation/gz/tests/test_gravenbol_map_alignment.py
```

The tests cover scale, the launch point, shoreline heights, shared world/GPS
configuration, collision references, triangle orientation and mesh normals.
Geofence checks cover edge/interior clearance, polygon intersections, coordinate
conversion, origin overrides and the PX4 fence-file format. The map regression
projects the generated GPS fence back into the supplied QGC screenshot and
rejects the old peninsula overlap; checking only fence-versus-mesh clearance
would miss a shared coordinate error. Regeneration is
deterministic.

## PX4 safety boundary

`geofence.py` defines a conservative 27-point inclusion polygon in the same
image coordinates as the traced shore. It covers the main basin and excludes
the narrow northern inlet. Edge samples are at most 0.5 m apart and currently
have 24.2 m minimum clearance from the traced shore: the intended 20 m buffer
plus allowance for the terrain grid. This is not an exact constant-distance
offset or a surveyed real-world boundary.

The fish_usv PX4 startup exports the Gazebo world to validate the terrain and
origin, converts the polygon from ENU to WGS84, and loads an instance-local
fence before MAVLink starts. A complete PX4_HOME_* override is applied only
after Gazebo acknowledges the new origin. PX4 restores the polygon and
Hold-on-breach action on each fish_usv restart. See `../fish_usv/README.md`
for QGC inspection, session overrides and limitations. Standalone Gazebo
does not enforce this autopilot fence.

Tested with Gazebo Harmonic 8.15 and PX4 SITL: both camera feeds rendered;
one falling probe settled on a dry bank and another on the submerged lakebed;
the USV floated at Z=0.13165 m. A two-waypoint mission completed and held
without joystick input. These are basic integration checks, not validation
against real lake measurements. A rendered overview is saved in the PX4
repository at `docs/gravenbol_sim_preview.png` (historical, before the corrected
beach-origin alignment).
