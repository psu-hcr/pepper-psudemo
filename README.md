# Pepper Python 2.7 / NAOqi Setup

This repository contains a minimal Python environment and example program for communicating with a Pepper robot using the NAOqi 2.5 Python SDK.

The setup uses:

* **Pepper:** NAOqi 2.5.10.7
* **NAOqi Python SDK:** `pynaoqi-python2.7-2.5.5.5-linux64`
* **Python:** 2.7.18
* **Example:** `hellopepper.py`
* **Network:** Local Wi-Fi router `fitzpitcel-media`

> **Important:** The NAOqi Python SDK used by Pepper 2.5 is built for Python 2.7. Do not use Python 3 to run `hellopepper.py`.

---

## 1. Install Python 2.7

This setup uses `pyenv` to manage Python 2.7 without replacing the system Python installation.

### Install pyenv

If `pyenv` is not already installed:

```bash
curl https://pyenv.run | bash
```

Follow the instructions printed by the installer to add `pyenv` to your shell configuration.

For Bash, this typically involves adding the following to `~/.bashrc`:

```bash
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
```

Then restart the terminal or reload the shell:

```bash
source ~/.bashrc
```

Verify that pyenv is available:

```bash
pyenv --version
```

### Install Python 2.7.18

Install Python 2.7.18:

```bash
pyenv install 2.7.18
```

Set Python 2.7.18 as the version for this repository:

```bash
pyenv local 2.7.18
```

This creates a `.python-version` file in the repository so that entering the repository automatically selects Python 2.7.18.

Verify:

```bash
python --version
```

You should see:

```text
Python 2.7.18
```

You can also verify the Python executable:

```bash
which python
```

It should point to something similar to:

```text
/home/<username>/.pyenv/shims/python
```

---

## 2. Download the NAOqi Python SDK

Download the NAOqi Python SDK:

**`pynaoqi-python2.7-2.5.5.5-linux64`**

> **SDK download:** [pynaoqi source zipped folder](https://pennstateoffice365-my.sharepoint.com/:u:/g/personal/kzf5356_psu_edu/IQCy5C7AfyTRR6l2LBuGUH3DAZ9CsM8eTxwuafMVQPzo5tY?e=j8YR3f)

Extract the ZIP file. For example:

```bash
mkdir -p ~/pynaoqi
cd ~/pynaoqi
unzip pynaoqi-python2.7-2.5.5.5-linux64.zip
```

After extraction, the directory structure should look approximately like:

```text
~/pynaoqi/
└── pynaoqi-python2.7-2.5.5.5-linux64/
    ├── bin/
    ├── lib/
    ├── share/
    └── ...
```

The Python NAOqi module should be located at:

```text
~/pynaoqi/pynaoqi-python2.7-2.5.5.5-linux64/lib/python2.7/site-packages/naoqi.py
```

---

## 3. Add the NAOqi Python module to PYTHONPATH

The NAOqi SDK is not installed through `pip`. Instead, Python needs to be told where the SDK's Python modules are located.

For the current terminal session, run:

```bash
export PYTHONPATH=$HOME/pynaoqi/pynaoqi-python2.7-2.5.5.5-linux64/lib/python2.7/site-packages:$PYTHONPATH
```

Verify that Python can find NAOqi:

```bash
python2.7 -c "import naoqi; print(naoqi.__file__)"
```

You should see something similar to:

```text
/home/<username>/pynaoqi/pynaoqi-python2.7-2.5.5.5-linux64/lib/python2.7/site-packages/naoqi.pyc
```

or:

```text
/home/<username>/pynaoqi/pynaoqi-python2.7-2.5.5.5-linux64/lib/python2.7/site-packages/naoqi.py
```

If this command succeeds, the NAOqi Python module is installed correctly.

---

## 4. Connect the computer and Pepper to the local network

Pepper and the computer running `hellopepper.py` must be on the **same local network**.

This setup uses the local Wi-Fi router:

```text
fitzpitcel-media
```

### Disconnect from the Internet

Before connecting to Pepper, disconnect the computer from its normal Internet connection.

For example, disconnect from:

* Ethernet
* PSU Wi-Fi
* eduroam
* Any other Wi-Fi network providing Internet access

### Connect to the Pepper network

Connect the computer to:

```text
fitzpitcel-media
```

Pepper should also already be connected to `fitzpitcel-media`.

The important requirement is:

```text
Computer
    │
    │ Wi-Fi
    │
fitzpitcel-media
    │
    │ Wi-Fi
    │
Pepper
```

The computer does **not** need Internet access while communicating with Pepper.

---

## 5. Determine Pepper's IP address

Before running the example, determine Pepper's IP address on the local network.

Pepper's IP address can be obtained from the robot's network information or another method appropriate to your network setup.

Once you know the IP address, verify that the computer can reach Pepper:

```bash
ping <PEPPER_IP_ADDRESS>
```

For example:

```bash
ping 192.168.1.100
```

You should receive responses from Pepper.

Stop the ping with:

```text
Ctrl+C
```

---

## 6. Run `hellopepper.py`

Make sure you are in the repository:

```bash
cd <path-to-this-repository>
```

Make sure the Python version is correct:

```bash
python --version
```

It should report:

```text
Python 2.7.18
```

Make sure the NAOqi SDK is available:

```bash
python2.7 -c "import naoqi; print(naoqi.__file__)"
```

Then run:

```bash
python2.7 hellopepper.py
```


---

## 7. Troubleshooting

### `ImportError: No module named naoqi`

This means Python cannot find the NAOqi SDK.

Check:

```bash
echo $PYTHONPATH
```

It should contain:

```text
pynaoqi-python2.7-2.5.5.5-linux64/lib/python2.7/site-packages
```

If not, run:

```bash
export PYTHONPATH=$HOME/pynaoqi/pynaoqi-python2.7-2.5.5.5-linux64/lib/python2.7/site-packages:$PYTHONPATH
```

Then test:

```bash
python2.7 -c "import naoqi; print(naoqi.__file__)"
```

---

### `python` is using Python 3

Check:

```bash
python --version
```

If the repository is configured with pyenv, run:

```bash
pyenv local 2.7.18
```

Then:

```bash
python --version
```

You should see:

```text
Python 2.7.18
```

You can also explicitly run:

```bash
python2.7 hellopepper.py
```

---

### Pepper cannot be reached

First check that both devices are connected to:

```text
fitzpitcel-media
```

Then test connectivity:

```bash
ping <PEPPER_IP_ADDRESS>
```

If there is no response, check the network connection before troubleshooting the Python program.

---

## 8. Quick-start commands

Once the environment has been set up, the typical workflow is:

```bash
# Enter the repository
cd <path-to-this-repository>

# Make sure pyenv is using Python 2.7
pyenv local 2.7.18

# Confirm Python version
python --version

# Add NAOqi to PYTHONPATH
export PYTHONPATH=$HOME/pynaoqi/pynaoqi-python2.7-2.5.5.5-linux64/lib/python2.7/site-packages:$PYTHONPATH

# Verify NAOqi
python2.7 -c "import naoqi; print(naoqi.__file__)"

# Connect to fitzpitcel-media and verify Pepper is reachable
ping <PEPPER_IP_ADDRESS>

# Run the example
python2.7 hellopepper.py
```

---

## Notes

This setup intentionally keeps the NAOqi Python environment separate from modern Python environments.

Pepper's NAOqi 2.5 Python SDK requires Python 2.7, while modern robotics development tools such as ROS 2 generally use Python 3. If ROS 2 integration is added later, the recommended approach is to keep the NAOqi Python 2.7 process separate and communicate with ROS 2 through an appropriate bridge or inter-process communication mechanism.


---

# Polar H10 heart-rate sensors → ROS 2 → dashboard → Pepper

Code lives in [`polar_ros2/`](polar_ros2/). It reads up to four Polar H10 chest straps over Bluetooth, publishes them as ROS 2 topics (`/p1` … `/p4`), and serves a live web dashboard (for a TV beside Pepper). This part uses **Python 3** and is separate from the Python 2.7 / NAOqi 2.5 setup above.

## What to download / install

| What | Why | How |
|---|---|---|
| Conda (Miniforge) | environment manager | <https://github.com/conda-forge/miniforge> |
| ROS 2 Jazzy (RoboStack on macOS, or native apt on Ubuntu 24.04) | topics, launch files | RoboStack: `conda create -n ros2 -c conda-forge -c robostack-jazzy ros-jazzy-desktop python=3.12` |
| colcon + rosdep | build the workspace | `conda install -n ros2 colcon-common-extensions rosdep` (apt: `python3-colcon-common-extensions`) |
| `bleak` | Bluetooth LE to the straps | `pip install bleak` |
| `qi` | NAOqi SDK for Pepper (NAOqi 2.9 and newer) | `pip install qi` |
| `opencv` (optional) | Mac webcam package `mac_camera` | included in `ros-jazzy-desktop` / `ros-jazzy-vision-opencv` |
| `pytest` (optional) | tests | `pip install pytest` |

The dashboard needs no extra packages and no internet.

Platform notes:
- **macOS:** allow Bluetooth for your terminal app (System Settings → Privacy & Security → Bluetooth). Allow incoming connections for Python the first time so a TV can reach the dashboard.
- **Linux:** needs BlueZ (`sudo apt install bluez`), and the Bluetooth service running.
- **Windows:** Bluetooth must be on; use a ROS 2 Windows install or WSL (WSL has no Bluetooth by default).
- The straps only advertise when **worn with wet electrodes**. Close Polar Beat and any phone app that is connected to them first.

## Build and run

```bash
conda activate ros2
cd polar_ros2
colcon build                 # plain build; do not use --symlink-install
source install/setup.zsh     # or setup.bash

ros2 launch polar_dashboard all.launch.py use_mock:=true   # fake data, no straps needed
ros2 launch polar_dashboard all.launch.py                  # real straps
```

Open `http://localhost:8765`, or `http://<computer-ip>:8765` from the TV's browser (same Wi-Fi).

## Finding the straps (works on macOS, Windows and Linux)

Each strap is listed in `polar_ros2/src/polar_h10_ros/config/sensors.yaml` with a `name` (the ROS namespace) and its `device_id`, the part after `Polar H10` in its Bluetooth name (e.g. `18D51C3F`). By default the node **scans for that name**, so the same file works on any computer.

`address` is an optional shortcut that skips the scan:
- macOS: the CoreBluetooth UUID (only valid on that Mac)
- Windows / Linux: the Bluetooth MAC, e.g. `A0:9E:1A:12:34:56`

To list nearby straps and their addresses on the current computer: `python polar_ros2/scan.py`. Re-run `colcon build` after editing the yaml.

## Topics

`/p1/polar_h10/heart_rate` … `/p4/…` (`Int32`), plus `rr_intervals`, `sensor_contact` and `connected`. The first three are best-effort QoS, so subscribers must also use best-effort (`ros2 topic echo --qos-reliability best_effort …`).

## Pepper

`python polar_ros2/tools/pepper_check.py <PEPPER_IP>` connects with `qi`, prints version and battery, and has Pepper say hello. This needs a Pepper running NAOqi 2.9 or newer; for NAOqi 2.5 use the Python 2.7 setup at the top of this README. Further integration (a node that reacts to the heart-rate topics) is still to do.

Tests: `cd polar_ros2/src/polar_h10_ros && python -m pytest test`

Full commands: [`polar_ros2/SETUP.md`](polar_ros2/SETUP.md).
