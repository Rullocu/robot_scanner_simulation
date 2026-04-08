source /opt/ros/humble/setup.bash
source install/setup.bash

docker exec -it ros2_container /bin/bash

ros2 run hardware_simulation item_mock

ros2 run hardware_simulation robot_mock

ros2 run hardware_simulation scanner_mock

ros2 run hardware_simulation pusher_mock

ros2 run hardware_simulation table_sensor_mock 

ros2 service call /item/spawn scan_table_interfaces/srv/SpawnItem "{}"

ros2 service call /robot/move scan_table_interfaces/srv/MoveRobot "{target_position: 1}"

ros2 service call /scanner/trigger scan_table_interfaces/srv/TriggerScan "{}"

# Push to pocket (item must be on scan table first)
ros2 service call /pusher/push scan_table_interfaces/srv/Push "{direction: 0}"