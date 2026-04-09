# Scan Table System

This is an robot-scanner-pusher table simulator, demostrating the following workflow
1.Robot picks and places item on the Scan Table
2.The system acquires barcodes from the scanners.
3.System assigns barcodes to the item
4.System actuates the pusher to clear the table.
5.The system signals ready-for-next-item only once the table is confirmed clear



## system modules
(briefly explaining the tasks of the five packages using words)
the system architecture is illustrated in ./docs/system_architecture.png

## scan_table_manager statemachine
(breifly explain the worflow of the statemachine in words)
the state diagram is illustrated in ./docs/state_diagram.png

## local deployment

prerequisit : docker
sudo ./run_ros2_docker_no_display.sh
it automautically detected if the container is build, and build it if not,
and then enter the container, and mount the src, build, log, install folder as volume.

after enter the container, use 
colcon build 
to build the workspace.

after build, source the workspace
source install/setup.bash

this will only need to be done once after the first build. later the entrypoint.sh will automatically source the workspace.

then the system is ready to use.

### launch system

this will lauch the scan_table_manager and all the hardware simulation nodes.
the state machine will run in 1hz step, and you can observe the state machine running in the terminal.
ros2 launch robot_scanner_bringup bringup.launch.py

the output will be like this:
[scan_table_manager-1] [INFO] [1775724470.646316821] [scan_table_manager]: CHECK_TABLE_OCCUPIED -> RECOVER_ROBOT  (occupied == false)
[robot_mock-3] [INFO] [1775724472.191793719] [robot_mock]: Robot moved to position 0
[scan_table_manager-1] [INFO] [1775724472.192068717] [scan_table_manager]: RECOVER_ROBOT -> PREPARE_ITEM  (MoveRobot to RED_TOTE success)
[item_mock-2] [INFO] [1775724472.705915410] [item_mock]: Spawned item 27 with 5 barcodes, weight=3.98 kg
[scan_table_manager-1] [INFO] [1775724472.706291613] [scan_table_manager]: Spawned item id=27
[scan_table_manager-1] [INFO] [1775724472.706331340] [scan_table_manager]: PREPARE_ITEM -> PICK_ITEM  (SpawnItem success, item_id=27)
[item_mock-2] [INFO] [1775724474.219562093] [item_mock]: Item 27 moved to position 1
[robot_mock-3] [INFO] [1775724474.245372811] [robot_mock]: Robot moved to position 1
[scan_table_manager-1] [INFO] [1775724474.245745910] [scan_table_manager]: PICK_ITEM -> VERIFY_ITEM_ON_TABLE  (MoveRobot to SCAN_TABLE success)
[scan_table_manager-1] [INFO] [1775724475.215954073] [scan_table_manager]: VERIFY_ITEM_ON_TABLE -> SCAN_ITEM  (occupied == true after pick)
[scanner_mock-4] [INFO] [1775724475.754288062] [scanner_mock]: Scan complete: 5 barcodes found
[scan_table_manager-1] [INFO] [1775724475.754581627] [scan_table_manager]: SCAN_ITEM -> ITEM_MANAGEMENT  (scan success, 5 barcode(s) found)
[scan_table_manager-1] [INFO] [1775724476.570020717] [scan_table_manager]: Item 27 — 1 unique barcode(s):
[scan_table_manager-1] [INFO] [1775724476.570089779] [scan_table_manager]:   barcode_id=0057f48e  face=0  total_seen=1

for better observation, you can open a second terminal, enter the docker container using 
 docker exec -it ros2_container /bin/bash
once enter, the entrypoint.sh will automatically source the workspace. you can directly run the monitor node.

ros2 run scanning_process_monitor monitor

ideally you can see output like this:
illustrated in ./docs/monitor.png




