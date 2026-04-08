from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='scan_table_manager',
            executable='scan_table_manager',
            name='scan_table_manager',
            output='screen',
        ),
    ])
