from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([Node(package='mac_camera', executable='mac_camera_node', output='screen')])
