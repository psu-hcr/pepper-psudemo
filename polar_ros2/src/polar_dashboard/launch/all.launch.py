"""Start the four strap nodes AND the dashboard together.

    ros2 launch polar_dashboard all.launch.py use_mock:=true   # fake data
    ros2 launch polar_dashboard all.launch.py                  # real straps
Then open http://localhost:8765 (or http://<laptop-ip>:8765 from the TV).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    polar_launch = os.path.join(get_package_share_directory('polar_h10_ros'),
                                'launch', 'polar_h10_multi.launch.py')
    return LaunchDescription([
        DeclareLaunchArgument('use_mock', default_value='false'),
        DeclareLaunchArgument('port', default_value='8765'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(polar_launch),
            launch_arguments={'use_mock': LaunchConfiguration('use_mock')}.items()),
        Node(package='polar_dashboard', executable='dashboard_node', output='screen',
             parameters=[{'port': ParameterValue(LaunchConfiguration('port'), value_type=int)}]),
    ])
