source /opt/ros/humble/setup.bash
source /setup.bash

docker exec -it ros2_container /bin/bash

ros2 run hardware_simulation item_mock

ros2 run hardware_simulation robot_mock

ros2 service call /item/spawn scan_table_interfaces/srv/SpawnItem "{}"

ros2 service call /robot/move scan_table_interfaces/srv/MoveRobot "{target_position: 1}"