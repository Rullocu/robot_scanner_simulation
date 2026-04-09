# Scan Table System

This is an robot-scanner-pusher table simulator, demostrating the following workflow
1. Robot picks and places item on the Scan Table
2. The system acquires barcodes from the scanners.
3. System assigns barcodes to the item
4. System actuates the pusher to clear the table.
5. The system signals ready-for-next-item only once the table is confirmed clear



## system modules

The system is composed of five packages:

- **scan_table_interfaces** — shared ROS2 message and service definitions used across all packages.
- **hardware_simulation** — five mock nodes that simulate the physical hardware:
  - `item_mock` — ground truth for item position and barcode data; handles spawn and move requests.
  - `robot_mock` — simulates the robot arm; moves between RED_TOTE and SCAN_TABLE, carrying the item when picking.
  - `scanner_mock` — simulates six face-scanners; returns barcodes found on the item when triggered.
  - `pusher_mock` — simulates the pusher mechanism; moves the item to POCKET or REJECT_AREA on command.
  - `table_sensor_mock` — simulates a weight/presence sensor; reports scan table occupancy derived from item state.
- **scan_table_manager** — the central C++ state machine node that orchestrates the full workflow by calling hardware services and reacting to sensor topics.
- **scanning_process_monitor** — a read-only Python monitor node that renders a live terminal dashboard showing state machine status, positions, sensor readings, and a rolling log.
- **robot_scanner_bringup** — top-level launch package that starts all hardware simulation nodes and the scan_table_manager together.

![system architecture](./docs/system_architecture.png)

## scan_table_manager state machine

The state machine runs at 1 Hz and drives the following repeating cycle:

1. **INIT** — entry point, transitions immediately to PREPARE_ITEM.
2. **PREPARE_ITEM** — spawns a new item in the RED_TOTE via `/item/spawn`.
3. **PICK_ITEM** — commands the robot to pick the item and place it on the scan table via `/robot/move`.
4. **VERIFY_ITEM_ON_TABLE** — confirms the scan table sensor reports `occupied=true` before proceeding.
5. **SCAN_ITEM** — triggers the barcode scanners via `/scanner/trigger` and collects results.
6. **ITEM_MANAGEMENT** — deduplicates barcodes, updates the item library, and validates that all barcodes belong to a single item. Routes to pocket if valid, or to error recovery if conflicting IDs are found.
7. **PUSH_ITEM_TO_POCKET** — actuates the pusher toward POCKET via `/pusher/push`.
8. **CHECK_TABLE_OCCUPIED** — checks whether the table is clear after pushing; if still occupied, routes to CLEAN_SCAN_TABLE.
9. **CLEAN_SCAN_TABLE** — pushes the item toward REJECT_AREA as a fallback clearance step.
10. **RECOVER_ROBOT** — returns the robot to RED_TOTE, ready for the next cycle.
11. **ERROR_RECOVERY** — logs the error, waits 2 seconds, and retries from PREPARE_ITEM.

On any service call failure the machine falls into **ERROR_RECOVERY** and retries. Hardware mocks simulate a 5% random failure rate to exercise these paths.

![state diagram](./docs/state_diagram.png)

## local deployment

prerequisit : docker
```bash
sudo ./run_ros2_docker_no_display.sh
```
It automatically detects if the container is built, builds it if not, then enters the container and mounts the `src`, `build`, `log`, and `install` folders as volumes.

After entering the container, build the workspace:
```bash
colcon build
```

Then source the workspace:
```bash
source install/setup.bash
```

This only needs to be done once after the first build. Subsequently, `entrypoint.sh` will automatically source the workspace on container entry.

### launch system

This launches the scan_table_manager and all hardware simulation nodes. The state machine runs at 1 Hz.

```bash
ros2 launch robot_scanner_bringup bringup.launch.py
```

The output will look like this:

```
[scan_table_manager-1] [INFO] [scan_table_manager]: CHECK_TABLE_OCCUPIED -> RECOVER_ROBOT  (occupied == false)
[robot_mock-3]         [INFO] [robot_mock]:          Robot moved to position 0
[scan_table_manager-1] [INFO] [scan_table_manager]: RECOVER_ROBOT -> PREPARE_ITEM  (MoveRobot to RED_TOTE success)
[item_mock-2]          [INFO] [item_mock]:           Spawned item 27 with 5 barcodes, weight=3.98 kg
[scan_table_manager-1] [INFO] [scan_table_manager]: Spawned item id=27
[scan_table_manager-1] [INFO] [scan_table_manager]: PREPARE_ITEM -> PICK_ITEM  (SpawnItem success, item_id=27)
[item_mock-2]          [INFO] [item_mock]:           Item 27 moved to position 1
[robot_mock-3]         [INFO] [robot_mock]:          Robot moved to position 1
[scan_table_manager-1] [INFO] [scan_table_manager]: PICK_ITEM -> VERIFY_ITEM_ON_TABLE  (MoveRobot to SCAN_TABLE success)
[scan_table_manager-1] [INFO] [scan_table_manager]: VERIFY_ITEM_ON_TABLE -> SCAN_ITEM  (occupied == true after pick)
[scanner_mock-4]       [INFO] [scanner_mock]:        Scan complete: 5 barcodes found
[scan_table_manager-1] [INFO] [scan_table_manager]: SCAN_ITEM -> ITEM_MANAGEMENT  (scan success, 5 barcode(s) found)
[scan_table_manager-1] [INFO] [scan_table_manager]: Item 27 — 1 unique barcode(s):
[scan_table_manager-1] [INFO] [scan_table_manager]:   barcode_id=0057f48e  face=0  total_seen=1
```

### monitor

For better observation, open a second terminal and enter the container:
```bash
docker exec -it ros2_container /bin/bash
```
Once inside, the workspace is sourced automatically. Run the monitor node:
```bash
ros2 run scanning_process_monitor monitor
```

![monitor](./docs/monitor.png)
