"""Launch the Polar H10 publisher (real or mock) with parameters from config/polar_h10.yaml.

    ros2 launch polar_h10_ros polar_h10.launch.py                 # real strap
    ros2 launch polar_h10_ros polar_h10.launch.py use_mock:=true  # fake sine-wave HR
    ros2 launch polar_h10_ros polar_h10.launch.py params_file:=/path/to/my.yaml

Exactly one of the two nodes starts, chosen by `use_mock`. Both read the same
YAML; each takes only the section whose key matches its node name.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_params = os.path.join(get_package_share_directory('polar_h10_ros'),
                                  'config', 'polar_h10.yaml')
    use_mock = LaunchConfiguration('use_mock')
    params_file = LaunchConfiguration('params_file')

    return LaunchDescription([
        DeclareLaunchArgument('use_mock', default_value='false',
                              description='Publish fake sine-wave HR instead of using the strap'),
        DeclareLaunchArgument('params_file', default_value=default_params,
                              description='YAML file with node parameters'),
        Node(
            package='polar_h10_ros',
            executable='polar_h10_node',
            name='polar_h10_node',
            parameters=[params_file],
            output='screen',
            condition=UnlessCondition(use_mock),
        ),
        Node(
            package='polar_h10_ros',
            executable='mock_polar_h10_node',
            name='mock_polar_h10_node',
            parameters=[params_file],
            output='screen',
            condition=IfCondition(use_mock),
        ),
    ])
