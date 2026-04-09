#include <chrono>
#include <map>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "scan_table_interfaces/msg/manager_state.hpp"
#include "scan_table_interfaces/msg/robot_status.hpp"
#include "scan_table_interfaces/msg/table_occupancy.hpp"
#include "scan_table_interfaces/srv/move_robot.hpp"
#include "scan_table_interfaces/srv/push.hpp"
#include "scan_table_interfaces/srv/spawn_item.hpp"
#include "scan_table_interfaces/srv/trigger_scan.hpp"

using namespace std::chrono_literals;

// ── position / direction constants ──────────────────────────────────────────
static constexpr uint8_t POS_RED_TOTE   = 0;
static constexpr uint8_t POS_SCAN_TABLE = 1;
static constexpr uint8_t DIR_POCKET     = 0;
static constexpr uint8_t DIR_REJECT     = 1;

// ── state machine states ─────────────────────────────────────────────────────
enum class State {
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

static const char * state_name(State s)
{
  switch (s) {
    case State::INIT:                 return "INIT";
    case State::PREPARE_ITEM:         return "PREPARE_ITEM";
    case State::PICK_ITEM:            return "PICK_ITEM";
    case State::VERIFY_ITEM_ON_TABLE: return "VERIFY_ITEM_ON_TABLE";
    case State::SCAN_ITEM:            return "SCAN_ITEM";
    case State::ITEM_MANAGEMENT:      return "ITEM_MANAGEMENT";
    case State::PUSH_ITEM_TO_POCKET:  return "PUSH_ITEM_TO_POCKET";
    case State::CHECK_TABLE_OCCUPIED: return "CHECK_TABLE_OCCUPIED";
    case State::CLEAN_SCAN_TABLE:     return "CLEAN_SCAN_TABLE";
    case State::RECOVER_ROBOT:        return "RECOVER_ROBOT";
    case State::ERROR_RECOVERY:       return "ERROR_RECOVERY";
    default:                          return "UNKNOWN";
  }
}

// ── node ─────────────────────────────────────────────────────────────────────
class ScanTableManager : public rclcpp::Node
{
public:
  ScanTableManager()
  : Node("scan_table_manager"), current_state_(State::INIT)
  {
    // subscriptions
    occupancy_sub_ = create_subscription<scan_table_interfaces::msg::TableOccupancy>(
      "/scan_table/occupancy", 10,
      [this](scan_table_interfaces::msg::TableOccupancy::SharedPtr msg) {
        latest_occupancy_ = *msg;
      });

    robot_status_sub_ = create_subscription<scan_table_interfaces::msg::RobotStatus>(
      "/robot/status", 10,
      [this](scan_table_interfaces::msg::RobotStatus::SharedPtr msg) {
        latest_robot_status_ = *msg;
      });

    // service clients
    move_robot_client_  = create_client<scan_table_interfaces::srv::MoveRobot>("/robot/move");
    spawn_item_client_  = create_client<scan_table_interfaces::srv::SpawnItem>("/item/spawn");
    trigger_scan_client_= create_client<scan_table_interfaces::srv::TriggerScan>("/scanner/trigger");
    push_client_        = create_client<scan_table_interfaces::srv::Push>("/pusher/push");

    // publisher
    state_pub_ = create_publisher<scan_table_interfaces::msg::ManagerState>("/manager/state", 10);

    // state machine timer — runs every 1000 ms
    timer_ = create_wall_timer(1000ms, [this]() { step(); });

    // state publisher timer — runs every 100 ms (10 Hz)
    pub_timer_ = create_wall_timer(100ms, [this]() { publish_state(); });

    RCLCPP_INFO(get_logger(), "ScanTableManager started");
  }

private:
  // ── state machine step ───────────────────────────────────────────────────
  void step()
  {
    // Only one async operation at a time; block re-entry while waiting.
    if (waiting_for_service_) {return;}

    RCLCPP_DEBUG(get_logger(), "State: %s", state_name(current_state_));

    switch (current_state_) {
      case State::INIT:
        transition(State::PREPARE_ITEM, "init complete");
        break;

      case State::CHECK_TABLE_OCCUPIED:
        if (latest_occupancy_.occupied) {
          transition(State::CLEAN_SCAN_TABLE, "occupied == true");
        } else {
          transition(State::RECOVER_ROBOT, "occupied == false");
        }
        break;

      case State::CLEAN_SCAN_TABLE:
        call_push(DIR_REJECT, State::RECOVER_ROBOT, State::ERROR_RECOVERY,
          "Push REJECT success", "Push REJECT failed");
        break;

      case State::RECOVER_ROBOT:
        call_move_robot(POS_RED_TOTE, State::PREPARE_ITEM, State::ERROR_RECOVERY,
          "MoveRobot to RED_TOTE success", "MoveRobot to RED_TOTE failed");
        break;

      case State::PREPARE_ITEM:
        call_spawn_item(State::PICK_ITEM, State::ERROR_RECOVERY);
        break;

      case State::PICK_ITEM:
        call_move_robot(POS_SCAN_TABLE, State::VERIFY_ITEM_ON_TABLE, State::ERROR_RECOVERY,
          "MoveRobot to SCAN_TABLE success", "MoveRobot to SCAN_TABLE failed");
        break;

      case State::VERIFY_ITEM_ON_TABLE:
        waiting_for_service_ = true;
        sleep_timer_ = create_wall_timer(500ms, [this]() {
          sleep_timer_->cancel();
          waiting_for_service_ = false;
          if (latest_occupancy_.occupied) {
            transition(State::SCAN_ITEM, "occupied == true after pick");
          } else {
            transition(State::ERROR_RECOVERY, "occupied == false after pick, item missing");
          }
        });
        break;

      case State::SCAN_ITEM:
        call_trigger_scan();
        break;

      case State::ITEM_MANAGEMENT:
        do_item_management();
        break;

      case State::PUSH_ITEM_TO_POCKET:
        call_push(DIR_POCKET, State::CHECK_TABLE_OCCUPIED, State::ERROR_RECOVERY,
          "Push POCKET success", "Push POCKET failed");
        break;

      case State::ERROR_RECOVERY:
        RCLCPP_ERROR(get_logger(), "ERROR_RECOVERY: manual intervention required");
        waiting_for_service_ = true;
        // sleep 2 s then continue
        sleep_timer_ = create_wall_timer(2000ms, [this]() {
          sleep_timer_->cancel();
          waiting_for_service_ = false;
          transition(State::PREPARE_ITEM, "error recovery complete, retrying");
        });
        break;
    }
  }

  // ── transition helper ────────────────────────────────────────────────────
  void transition(State next, const std::string & reason = "")
  {
    last_transition_   = std::string(state_name(current_state_)) + " -> " + state_name(next);
    transition_reason_ = reason;
    RCLCPP_INFO(get_logger(), "%s -> %s  (%s)",
      state_name(current_state_), state_name(next), reason.c_str());
    current_state_ = next;
  }

  // ── state publisher ───────────────────────────────────────────────────────
  void publish_state()
  {
    auto msg = scan_table_interfaces::msg::ManagerState();
    msg.state              = static_cast<uint8_t>(current_state_);
    msg.state_name         = state_name(current_state_);
    msg.last_transition    = last_transition_;
    msg.transition_reason  = transition_reason_;
    msg.current_item_id    = current_item_id_;
    msg.item_library_size  = static_cast<uint32_t>(item_library_.size());
    state_pub_->publish(msg);
  }

  // ── service call helpers ─────────────────────────────────────────────────
  void call_move_robot(uint8_t target, State on_success, State on_failure,
    const std::string & reason_success, const std::string & reason_failure)
  {
    if (!move_robot_client_->wait_for_service(0s)) {
      RCLCPP_WARN(get_logger(), "/robot/move not available yet");
      return;
    }
    waiting_for_service_ = true;
    auto req = std::make_shared<scan_table_interfaces::srv::MoveRobot::Request>();
    req->target_position = target;
    move_robot_client_->async_send_request(
      req,
      [this, on_success, on_failure, reason_success, reason_failure](
        rclcpp::Client<scan_table_interfaces::srv::MoveRobot>::SharedFuture future)
      {
        waiting_for_service_ = false;
        auto res = future.get();
        if (res->success) {
          transition(on_success, reason_success);
        } else {
          RCLCPP_WARN(get_logger(), "MoveRobot failed: %s", res->error_message.c_str());
          transition(on_failure, reason_failure);
        }
      });
  }

  void call_spawn_item(State on_success, State on_failure)
  {
    if (!spawn_item_client_->wait_for_service(0s)) {
      RCLCPP_WARN(get_logger(), "/item/spawn not available yet");
      return;
    }
    waiting_for_service_ = true;
    auto req = std::make_shared<scan_table_interfaces::srv::SpawnItem::Request>();
    spawn_item_client_->async_send_request(
      req,
      [this, on_success, on_failure](
        rclcpp::Client<scan_table_interfaces::srv::SpawnItem>::SharedFuture future)
      {
        waiting_for_service_ = false;
        auto res = future.get();
        if (res->success) {
          current_item_id_ = res->item_id;
          RCLCPP_INFO(get_logger(), "Spawned item id=%u", current_item_id_);
          transition(on_success, "SpawnItem success, item_id=" + std::to_string(res->item_id));
        } else {
          RCLCPP_WARN(get_logger(), "SpawnItem failed: %s", res->error_message.c_str());
          transition(on_failure, "SpawnItem failed: " + res->error_message);
        }
      });
  }

  void call_trigger_scan()
  {
    if (!trigger_scan_client_->wait_for_service(0s)) {
      RCLCPP_WARN(get_logger(), "/scanner/trigger not available yet");
      return;
    }
    waiting_for_service_ = true;
    auto req = std::make_shared<scan_table_interfaces::srv::TriggerScan::Request>();
    trigger_scan_client_->async_send_request(
      req,
      [this](
        rclcpp::Client<scan_table_interfaces::srv::TriggerScan>::SharedFuture future)
      {
        waiting_for_service_ = false;
        auto res = future.get();
        if (!res->success) {
          RCLCPP_WARN(get_logger(), "TriggerScan failed: %s", res->error_message.c_str());
          transition(State::ERROR_RECOVERY, "TriggerScan failed: " + res->error_message);
          return;
        }
        if (res->barcodes.empty()) {
          RCLCPP_INFO(get_logger(), "Scan returned 0 barcodes -> CLEAN_SCAN_TABLE");
          transition(State::CLEAN_SCAN_TABLE, "scan success, barcodes == 0");
          return;
        }
        current_barcodes_.assign(res->barcodes.begin(), res->barcodes.end());
        transition(State::ITEM_MANAGEMENT,
          "scan success, " + std::to_string(res->barcodes.size()) + " barcode(s) found");
      });
  }

  void call_push(uint8_t direction, State on_success, State on_failure,
    const std::string & reason_success, const std::string & reason_failure)
  {
    if (!push_client_->wait_for_service(0s)) {
      RCLCPP_WARN(get_logger(), "/pusher/push not available yet");
      return;
    }
    waiting_for_service_ = true;
    auto req = std::make_shared<scan_table_interfaces::srv::Push::Request>();
    req->direction = direction;
    push_client_->async_send_request(
      req,
      [this, on_success, on_failure, reason_success, reason_failure](
        rclcpp::Client<scan_table_interfaces::srv::Push>::SharedFuture future)
      {
        waiting_for_service_ = false;
        auto res = future.get();
        if (res->success) {
          transition(on_success, reason_success);
        } else {
          RCLCPP_WARN(get_logger(), "Push failed: %s", res->error_message.c_str());
          transition(on_failure, reason_failure);
        }
      });
  }

  // ── ITEM_MANAGEMENT ──────────────────────────────────────────────────────
  void do_item_management()
  {
    // deduplicate by barcode_id
    std::map<std::string, uint8_t> seen;   // barcode_id → face
    for (auto & bc : current_barcodes_) {
      seen[bc.barcode_id] = bc.face;
    }

    // update item library
    for (auto & [id, face] : seen) {
      item_library_[id]++;
    }

    // log
    RCLCPP_INFO(get_logger(), "Item %u — %zu unique barcode(s):", current_item_id_, seen.size());
    for (auto & [id, face] : seen) {
      RCLCPP_INFO(get_logger(), "  barcode_id=%s  face=%u  total_seen=%u",
        id.c_str(), face, item_library_[id]);
    }

    // check all barcode_ids identical (only one unique id)
    if (seen.size() == 1) {
      transition(State::PUSH_ITEM_TO_POCKET, "single unique barcode_id");
    } else {
      RCLCPP_WARN(get_logger(), "Multiple distinct barcode IDs — ERROR_RECOVERY");
      transition(State::ERROR_RECOVERY, "multiple distinct barcode IDs detected");
    }
  }

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

// ── main ─────────────────────────────────────────────────────────────────────
int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ScanTableManager>());
  rclcpp::shutdown();
  return 0;
}
