from glob import glob
from setuptools import setup

package_name = 'polar_dashboard'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/web', glob('web/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Palak',
    maintainer_email='palakchauhan.niyati@gmail.com',
    description='Web dashboard for Polar H10 heart rate.',
    license='MIT',
    entry_points={'console_scripts': ['dashboard_node = polar_dashboard.dashboard_node:main']},
)
