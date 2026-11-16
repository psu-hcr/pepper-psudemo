"""Launch one polar_h10_node per strap listed in config/sensors.yaml.

    ros2 launch polar_h10_ros polar_h10_multi.launch.py                # 4 real straps
    ros2 launch polar_h10_ros polar_h10_multi.launch.py use_mock:=true # 4 fake sine waves

Each strap gets its own namespace (p1..p4): /p1/polar_h10/heart_rate, ...
If a strap has an `address` it is used directly (MAC on Windows/Linux, UUID on macOS);
if blank, the node scans for the strap named "Polar H10 <device_id>", so one
config works on any OS and two nodes never grab the same strap.
"""
import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('polar_h10_ros')
    default_sensors = os.path.join(share, 'config', 'sensors.yaml')
    # Read at launch time with the default path; override by editing sensors.yaml.
    with open(default_sensors) as f:
        sensors = yaml.safe_load(f)['sensors']

    use_mock = LaunchConfiguration('use_mock')
    actions = [DeclareLaunchArgument('use_mock', default_value='false',
                                     description='Fake heart rates instead of real straps')]

    for s in sensors:
        actions.append(Node(
            package='polar_h10_ros', executable='polar_h10_node',
            namespace=s['name'], name='polar_h10_node', output='screen',
            parameters=[{'device_address': str(s.get('address') or ''),
                         'device_id': str(s.get('device_id') or '')}],
            condition=UnlessCondition(use_mock)))
        actions.append(Node(
            package='polar_h10_ros', executable='mock_polar_h10_node',
            namespace=s['name'], name='mock_polar_h10_node', output='screen',
            condition=IfCondition(use_mock)))
    return LaunchDescription(actions)
