source /opt/ros/humble/setup.bash
source /setup.bash

docker exec -it ros2_container /bin/bash

ros2 service call /item/spawn scan_table_interfaces/srv/SpawnItem "{}"