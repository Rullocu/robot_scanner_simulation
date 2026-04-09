#pragma once

#include <map>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "scan_table_interfaces/msg/barcode.hpp"
#include "scan_table_interfaces/msg/manager_state.hpp"
#include "scan_table_interfaces/msg/robot_status.hpp"
#include "scan_table_interfaces/msg/table_occupancy.hpp"
#include "scan_table_interfaces/srv/move_robot.hpp"
#include "scan_table_interfaces/srv/push.hpp"
#include "scan_table_interfaces/srv/spawn_item.hpp"
#include "scan_table_interfaces/srv/trigger_scan.hpp"

namespace scan_table_manager
{

// ── position / direction constants ──────────────────────────────────────────
constexpr uint8_t POS_RED_TOTE   = 0;
constexpr uint8_t POS_SCAN_TABLE = 1;
constexpr uint8_t DIR_POCKET     = 0;
constexpr uint8_t DIR_REJECT     = 1;

// ── state machine states ─────────────────────────────────────────────────────
enum class State : uint8_t
{
  INIT,
  PREPARE_ITEM,
  PICK_ITEM,
  VERIFY_ITEM_ON_TABLE,
  SCAN_ITEM,
  ITEM_MANAGEMENT,
  PUSH_ITEM_TO_POCKET,
  CHECK_TABLE_OCCUPIED,
  CLEAN_SCAN_TABLE,
  RECOVER_ROBOT,
  ERROR_RECOVERY,
};

const char * state_name(State s);

// ── node ─────────────────────────────────────────────────────────────────────
class ScanTableManager : public rclcpp::Node
{
public:
  explicit ScanTableManager();

private:
  // ── state machine ────────────────────────────────────────────────────────
  void step();
  void transition(State next, const std::string & reason = "");

  // ── state publisher ───────────────────────────────────────────────────────
  void publish_state();

  // ── service call helpers ──────────────────────────────────────────────────
  void call_move_robot(
    uint8_t target,
    State on_success, State on_failure,
    const std::string & reason_success, const std::string & reason_failure);

  void call_spawn_item(State on_success, State on_failure);

  void call_trigger_scan();

  void call_push(
    uint8_t direction,
    State on_success, State on_failure,
    const std::string & reason_success, const std::string & reason_failure);

  // ── item management ───────────────────────────────────────────────────────
  void do_item_management();

  // ── members ───────────────────────────────────────────────────────────────
  State current_state_;
  bool  waiting_for_service_{false};

  uint8_t current_item_id_{0};
  std::vector<scan_table_interfaces::msg::Barcode> current_barcodes_;
  std::map<std::string, uint32_t> item_library_;

  std::string last_transition_{"-> INIT"};
  std::string transition_reason_{"startup"};

  scan_table_interfaces::msg::TableOccupancy latest_occupancy_;
  scan_table_interfaces::msg::RobotStatus    latest_robot_status_;

  rclcpp::Subscription<scan_table_interfaces::msg::TableOccupancy>::SharedPtr occupancy_sub_;
  rclcpp::Subscription<scan_table_interfaces::msg::RobotStatus>::SharedPtr    robot_status_sub_;

  rclcpp::Publisher<scan_table_interfaces::msg::ManagerState>::SharedPtr state_pub_;

  rclcpp::Client<scan_table_interfaces::srv::MoveRobot>::SharedPtr   move_robot_client_;
  rclcpp::Client<scan_table_interfaces::srv::SpawnItem>::SharedPtr   spawn_item_client_;
  rclcpp::Client<scan_table_interfaces::srv::TriggerScan>::SharedPtr trigger_scan_client_;
  rclcpp::Client<scan_table_interfaces::srv::Push>::SharedPtr        push_client_;

  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::TimerBase::SharedPtr pub_timer_;
  rclcpp::TimerBase::SharedPtr sleep_timer_;
};

}  // namespace scan_table_manager
