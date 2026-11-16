# polar_h10_ros

ROS 2 (Humble) package that reads a **Polar H10** chest strap over Bluetooth Low
Energy and publishes heart rate, RR intervals and sensor contact as standard
`std_msgs` topics. It only publishes sensor data. Over-exertion logic and Pepper
behaviour belong in separate nodes that subscribe to these topics.

| Topic | Type | QoS | Meaning |
|---|---|---|---|
| `/polar_h10/heart_rate` | `std_msgs/Int32` | SENSOR_DATA | BPM, ~1 Hz |
| `/polar_h10/rr_intervals` | `std_msgs/Float32MultiArray` | SENSOR_DATA | seconds between beats, 0+ values per sample |
| `/polar_h10/sensor_contact` | `std_msgs/Bool` | SENSOR_DATA | strap electrodes touching skin |
| `/polar_h10/connected` | `std_msgs/Bool` | reliable (default) | BLE link up; sent on change and every 1 s |

SENSOR_DATA is *best-effort*. A subscriber that asks for *reliable* QoS will
connect but **receive nothing**. In your own subscriber nodes, use
`QoSPresetProfiles.SENSOR_DATA.value` for the first three topics.

## Layout

```
polar_h10_ros/
  hrm_parser.py           byte-level HRM packet parser (no ROS, no BLE)
  ble_worker.py           bleak connection + reconnect state machine, own thread (no ROS)
  polar_h10_node.py       rclpy node: params, publishers, drains the worker's queue
  mock_polar_h10_node.py  fake 60-120 BPM sine wave on the same topics
launch/polar_h10.launch.py
config/polar_h10.yaml
test/                     pytest: parser + reconnect logic with a fake BLE client
```

## Install

```bash
sudo apt install bluez python3-pip          # BlueZ is the Linux Bluetooth stack bleak talks to
pip install --user bleak
# The Polar/ folder is the colcon workspace; the package lives in Polar/src/.
# Copy the whole folder to the Ubuntu machine (e.g. as ~/Polar), then:
cd ~/Polar
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -y
colcon build --packages-select polar_h10_ros
source install/setup.bash                    # in every new terminal
```

## Find the H10's MAC address (Linux)

Put the strap on (it only advertises when the electrodes are wet and touching skin), then:

```
$ bluetoothctl
[bluetooth]# scan on
[NEW] Device A0:9E:1A:12:34:56 Polar H10 12345678
[bluetooth]# scan off
[bluetooth]# exit
```

Put that MAC in `config/polar_h10.yaml` as `device_address`, or leave it empty
so the node scans for anything named `Polar H10*`. **Do not pair it** in
bluetoothctl. The HR service needs no pairing, and a pairing record can get in the way.

## Run

```bash
ros2 launch polar_h10_ros polar_h10.launch.py                    # real strap
ros2 launch polar_h10_ros polar_h10.launch.py use_mock:=true     # no strap needed (SYNTHETIC)
```

Override a single parameter without editing YAML:

```bash
ros2 run polar_h10_ros polar_h10_node --ros-args -p device_address:=A0:9E:1A:12:34:56
```

## Verify

```bash
ros2 topic echo /polar_h10/heart_rate
ros2 topic echo /polar_h10/connected
ros2 topic hz /polar_h10/heart_rate          # expect ~1 Hz
rqt_plot /polar_h10/heart_rate/data
```

**Foxglove Studio:** run `ros2 launch foxglove_bridge foxglove_bridge_launch.xml`
(`sudo apt install ros-humble-foxglove-bridge`), connect Foxglove to
`ws://localhost:8765` and add a Plot panel on `/polar_h10/heart_rate.data`.
Every topic uses a standard message type, so no custom message
definitions are needed.

## Reading the logs

Every connection state change is logged at INFO with the tag `[polar_h10][state]`:

```
[polar_h10][state] IDLE -> SCANNING (up to 10s for "Polar H10*")
[polar_h10][state] SCANNING -> CONNECTING (Polar H10 12345678 [A0:9E:1A:12:34:56])
[polar_h10][state] CONNECTING -> CONNECTED (...)
[polar_h10][state] CONNECTED -> STREAMING
[polar_h10][ble] NotificationTimeout: no HR notification for 5.1s (limit 5.0s)
[polar_h10][state] STREAMING -> DISCONNECTED
[polar_h10][state] DISCONNECTED -> BACKOFF (retrying in 1s)
```

## Troubleshooting

- **`DeviceNotFound` on every scan.** The strap only advertises while worn with
  damp electrodes. It also accepts **one BLE connection at a time**, so close
  Polar Beat / Polar Flow / any phone app that is connected to it.
- **Stuck at `CONNECTED`, never `STREAMING`, then `NotificationTimeout`.** The
  link is up but no HR packets are arriving. Usually the electrodes are dry or
  the strap is not being worn.
- **`org.bluez.Error.NotReady` / `InProgress`.** Run `bluetoothctl power on`. If
  that doesn't help, run `sudo systemctl restart bluetooth`.
- **`ros2 topic echo` shows nothing but `connected` is true.** Check the QoS
  note above. Recent `ros2 topic echo` matches the publisher automatically; a
  custom subscriber must use SENSOR_DATA.
- **macOS:** `device_address` is a CoreBluetooth UUID, not a MAC. Leave it
  empty to scan, and the log line shows the UUID found.

## Tests

```bash
colcon test --packages-select polar_h10_ros && colcon test-result --verbose
# or without ROS, from the package dir:
python3 -m pytest test/
```
