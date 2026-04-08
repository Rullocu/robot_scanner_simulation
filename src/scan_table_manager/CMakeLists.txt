cmake_minimum_required(VERSION 3.8)
project(scan_table_manager)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(scan_table_interfaces REQUIRED)

add_executable(scan_table_manager src/scan_table_manager.cpp)
target_include_directories(scan_table_manager PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(scan_table_manager PUBLIC cxx_std_17)
ament_target_dependencies(scan_table_manager rclcpp scan_table_interfaces)

install(TARGETS scan_table_manager
  DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME})

ament_package()
