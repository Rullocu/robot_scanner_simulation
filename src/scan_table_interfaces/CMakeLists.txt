cmake_minimum_required(VERSION 3.8)
project(scan_table_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Barcode.msg"
  "msg/ItemState.msg"
  "msg/TableOccupancy.msg"
  "msg/RobotStatus.msg"
  "msg/ManagerState.msg"
  "srv/MoveRobot.srv"
  "srv/MoveItem.srv"
  "srv/SpawnItem.srv"
  "srv/TriggerScan.srv"
  "srv/Push.srv"
)

ament_package()
