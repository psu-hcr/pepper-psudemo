from glob import glob
from setuptools import setup

package_name = 'mac_camera'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Palak',
    maintainer_email='palakchauhan.niyati@gmail.com',
    description='Mac webcam publisher for ROS 2.',
    license='MIT',
    entry_points={'console_scripts': ['mac_camera_node = mac_camera.mac_camera_node:main']},
)
