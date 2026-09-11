# Fish USV

Gazebo Harmonic prototype for camera-based fish detection: a 1.2 m twin-hull
surface vessel with two independent thrusters, hydrodynamic damping, an underwater
RGB camera, and IMU, magnetometer, pressure and GNSS sensors. Geometry uses
primitives, so no mesh downloads are needed.

Run the integrated PX4 simulation from the PX4 repository root:

```bash
make px4_sitl gz_fish_usv
```

This starts PX4 SITL, the `fish_usv` Gazebo world, spawns `fish_usv_0`, and
starts the PX4-Gazebo sensor/actuator bridge. Start QGroundControl separately
with `qgc`; it normally connects to PX4 automatically.

Both worlds default to latitude **51.971659**, longitude **5.384925**.
Water-surface elevation remains an assumed 0 m, not a surveyed local elevation.
Close PX4 and Gazebo before relaunching to load a changed world origin.
Explicit `PX4_HOME_LAT`, `PX4_HOME_LON` and `PX4_HOME_ALT` environment variables
override the world coordinates; unset all three to use this default.
The GPS origin places the boat on QGC's map but does not load real terrain.

The world provides calm freshwater with its surface at world Z=0 and a seabed
at Z=-5 m. It spawns the boat at Z=0.131 m. Hull mass, inertia, thrust and drag
are initial estimates requiring calibration; waves and water optics are not modeled.
Each hull uses eight adjoining collision boxes. Gazebo Harmonic 8.15 does not
rotate the graded-buoyancy slicing plane for inclined boxes; subdividing the
hulls supplies longitudinal restoring forces as the bow and stern immerse.
The visual hulls and total displacement volume are unchanged.

After editing the model, exit PX4 and close the old Gazebo simulation before
relaunching. An already spawned boat retains its old physics. Wait for sensor
initialization, then run `commander check` in the PX4 terminal to verify preflight
readiness. The roll/pitch failure checks remain enabled.

PX4 maps rover motor 1 to the starboard propeller and motor 2 to the port
propeller. The model maps PX4's 1000--2000 motor output to reverse--forward
thrust, centred at 1500. Use QGroundControl's rover controls or a joystick to
arm and drive it.

The airframe selects `MAV_MAN_THR=1` for QGC's rover virtual joystick:
MAVLink throttle `z=-1000/0/1000` means reverse/neutral/forward. Enable QGC's
Auto-Center Throttle option so releasing the stick returns to neutral. PX4's
legacy mapping (`MAV_MAN_THR=0`) interprets `z=0` as full reverse and `z=500`
as neutral; using it with the signed QGC rover stick causes unintended reverse
on release. Other airframes retain that legacy default. If using a different
MAVLink joystick source, match this parameter to its range while disarmed.
This mapping does not change RC receiver inputs, mission control or the ESC
neutral output (1500). Rebuild and restart PX4 after installing this change.
An isolated SITL check exercised full forward and full reverse followed by
release: both motor outputs returned to 1500 without crossing into opposite
thrust. The legacy and signed input ranges were also checked independently.

For missions, upload ordinary rover waypoints in QGroundControl, then start
Mission mode. The airframe configures heading, yaw-rate and speed controllers;
in particular `RO_YAW_P` and `RO_YAW_RATE_LIM` must be nonzero. Manual mode
can still work when these mission-controller settings are missing.
Restart PX4 after changing airframe defaults so they are loaded. If you have
explicitly saved different values for these parameters, those overrides take
precedence over the airframe defaults.

`COM_RCL_EXCEPT=3` allows Mission and Hold to continue when QGC joystick
messages stop. Manual modes still trigger the configured failsafe on loss
of manual input. If upgrading a running simulation, set
`param set COM_RCL_EXCEPT 3` in its PX4 console, then select Mission again.
This setting is specific to the joystick-optional simulation workflow.

Validation: an isolated PX4 instance accepted a two-waypoint MAVLink mission
(approximately 5 m north, then 5 m east), reported both waypoints reached,
and finished in loiter with zero motor commands. This checks basic waypoint
execution; the controller values are still prototype simulation tuning.
A manual-input-loss regression also stopped a MAVLink joystick stream before
starting the mission: both waypoints completed and post-mission Hold remained
active without a failsafe while manual input was unavailable.

The camera looks straight down from between the hulls, below the waterline.
It produces RGB images at 1280 x 720, 20 Hz, with an 80-degree horizontal field
of view and a 20 m far clipping distance. In the PX4 simulation, the image topic is:

```text
/world/fish_usv/model/fish_usv_0/link/base_link/sensor/fish_camera/image
```

Use `gz topic -l` to discover topics if you rename the world or model.
To view the feed while the integrated simulation is running, open a second
terminal in the PX4 repository root and run:

```bash
gz gui -c Tools/simulation/gz/models/fish_usv/camera.config
```

This opens a normal GUI window with the camera topic preselected. Avoid
`gz gui -s ImageDisplay` on gz-gui 8.4: its topic notification can dereference
a missing main window and crash. The configuration uses a main window instead.
Keep the simulation unpaused. The current seabed has no texture or fish, so
the downward-facing image can look like a nearly uniform sandy colour even
when frames are arriving. For the standalone demo, choose the topic beginning
`/world/fish_usv_demo/model/fish_usv/` instead.

Add fish geometry below the surface and connect an image subscriber/detection
pipeline to this topic. The model does not include fish, a trained detector,
sonar, underwater attenuation, or detection ground-truth labels.

To run Gazebo without PX4, use the standalone demo:

```bash
export GZ_SIM_RESOURCE_PATH="$PWD/Tools/simulation/gz/models:${GZ_SIM_RESOURCE_PATH}"
gz sim -r Tools/simulation/gz/models/fish_usv/demo.sdf
```

The standalone demo is for inspecting the scene and sensors. It does not have
an autopilot or a control source; source
`build/px4_sitl_default/rootfs/gz_env.sh` first if you also want its PX4
motor plugin to load.

Plugin references: [Gazebo thrusters](https://gazebosim.org/api/sim/8/underwater_vehicles.html)
and the installed Harmonic `graded_buoyancy.sdf` example.
