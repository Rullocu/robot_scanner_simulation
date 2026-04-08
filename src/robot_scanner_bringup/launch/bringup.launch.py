from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    scan_table_manager_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('scan_table_manager'),
                'launch',
                'scan_table_manager.launch.py',
            )
        )
    )

    hardware_nodes = [
        Node(package='hardware_simulation', executable=exe, name=exe, output='screen')
        for exe in [
            'item_mock',
            'robot_mock',
            'scanner_mock',
            'pusher_mock',
            'table_sensor_mock',
        ]
    ]

    return LaunchDescription([scan_table_manager_launch] + hardware_nodes)
