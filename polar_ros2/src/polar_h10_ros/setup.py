"""setup.py - tells colcon how to install this ament_python package.

Two things matter for ROS:
  * `data_files` copies package.xml, the launch file and the YAML config into
    the install tree's `share/polar_h10_ros/`, which is where
    `get_package_share_directory()` and `ros2 launch` look for them.
  * `entry_points` creates the executables that `ros2 run polar_h10_ros <name>`
    and the launch file's `Node(executable=...)` start.
"""
from glob import glob

from setuptools import setup

package_name = 'polar_h10_ros'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Palak',
    maintainer_email='palakchauhan.niyati@gmail.com',
    description='Polar H10 BLE heart rate publisher for ROS 2.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'polar_h10_node = polar_h10_ros.polar_h10_node:main',
            'mock_polar_h10_node = polar_h10_ros.mock_polar_h10_node:main',
        ],
    },
)
