# Mac setup (RoboStack ROS 2 Jazzy)

Env: conda env `ros2` (RoboStack jazzy desktop, Python 3.12, arm64).

```bash
conda activate ros2
cd ~/Desktop/Polar
colcon build                 # do NOT use --symlink-install (new setuptools rejects it)
source install/setup.zsh     # zsh; use setup.bash only in bash
```

## Added on top of the base env
colcon, rosdep, rqt_image_view, image_transport, camera_calibration, tf2_tools,
robot_state_publisher, xacro, rosbridge_suite, vision_opencv, bleak (pip), qi (pip, NAOqi SDK).

## Packages in src/
- `polar_h10_ros`: Polar H10 BLE heart rate. Mock: `ros2 run polar_h10_ros mock_polar_h10_node`.
  Real strap: `ros2 launch polar_h10_ros polar_h10.launch.py` (set `device_id` in config/polar_h10.yaml
  to the ID in the strap's name, or `device_address`; see `python scan.py`).
  Subscribers must use best-effort QoS (`--qos-reliability best_effort` for `ros2 topic echo`).
- `mac_camera`: `ros2 run mac_camera mac_camera_node` -> `/camera/image_raw`.
  View: `ros2 run rqt_image_view rqt_image_view`. Needs macOS Camera permission for the app
  running the terminal (System Settings > Privacy & Security > Camera). `device:=1` for iPhone.

## Four straps
Straps live in `src/polar_h10_ros/config/sensors.yaml` (p1..p4, IDs 18D51C3F,
18D5793E, 18D5173A, 18D25430). Straps are found by `device_id` (works on macOS/Windows/Linux);
`address` is an optional shortcut (MAC on Windows/Linux, UUID on macOS). After editing, run `colcon build`.
- Fake data: `ros2 launch polar_h10_ros polar_h10_multi.launch.py use_mock:=true`
- Real straps: `ros2 launch polar_h10_ros polar_h10_multi.launch.py`
- Topics: `/p1/polar_h10/heart_rate` ... `/p4/polar_h10/heart_rate` (also rr_intervals,
  sensor_contact, connected). Straps only advertise when worn/wet; close Polar Beat/phone apps first.

## Dashboard (for the TV)
`ros2 launch polar_dashboard all.launch.py use_mock:=true` (fake data) or without `use_mock` (real
straps) starts the four strap nodes plus the web dashboard. Open `http://localhost:8765` on the
laptop, or `http://<laptop-ip>:8765` on the TV's browser (same Wi-Fi; `ipconfig getifaddr en0`).
Port 8080 is used by another program on this Mac, so the dashboard uses 8765 (`port:=NNNN` to change).
The page is copied at build time: after editing `web/index.html`, run `colcon build`.
Colour thresholds (display only, not medical): `elevated_bpm` 110, `high_bpm` 140 params of `dashboard_node`.
macOS may ask to allow incoming connections for Python the first time; allow it so the TV can connect.

## Pepper
- `python tools/pepper_check.py <PEPPER_IP>` connects with `qi`, prints version/battery, says hello.
- Mac and Pepper must be on the same network. Pepper IP: press her chest button.
- No `naoqi_driver2` conda package exists for RoboStack; talk to Pepper through `qi`
  from a ROS node (subscribe to /polar_h10/* and call ALTextToSpeech / ALMotion).
