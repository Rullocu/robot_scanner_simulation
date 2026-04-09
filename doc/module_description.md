# Module Boundary & Function Description
**Scan Table System — ROS2**

---

## Package: `scan_table_interfaces`

**Type:** ROS2 interfaces package (msg/srv only)

### Messages

#### `ManagerState.msg`
| Field | Type | Description |
|---|---|---|
| `state` | `uint8` | Current state enum value (matches State enum order) |
| `state_name` | `string` | Human-readable, e.g. `"SCAN_ITEM"` |
| `last_transition` | `string` | e.g. `"PICK_ITEM → VERIFY_ITEM_ON_TABLE"` |
| `transition_reason` | `string` | Human-readable reason, e.g. `"MoveRobot success"` |
| `current_item_id` | `uint8` | |
| `item_library_size` | `uint32` | Total unique barcode IDs accumulated so far |

- **Published by:** `scan_table_manager`
- **Subscribed by:** `scanning_process_monitor`

#### `ItemState.msg`
| Field | Type | Description |
|---|---|---|
| `item_id` | `uint8` | |
| `position` | `uint8` | `0=RED_TOTE, 1=SCAN_TABLE, 2=POCKET, 3=REJECT_AREA, 4=UNKNOWN` |
| `weight` | `float32` | |
| `barcodes` | `Barcode[]` | |

- **Published by:** `item_mock`
- **Subscribed by:** `robot_mock`, `scanner_mock`, `pusher_mock`, `table_sensor_mock`

#### `Barcode.msg`
| Field | Type | Description |
|---|---|---|
| `barcode_id` | `string` | |
| `face` | `uint8` | `0–5`, representing 6 faces of the item |

Sub-message used inside `ItemState` and `TriggerScan` response.

#### `TableOccupancy.msg`
| Field | Type | Description |
|---|---|---|
| `occupied` | `bool` | |
| `weight` | `float32` | |

- **Published by:** `table_sensor_mock`
- **Subscribed by:** `ScanTableManager`

#### `RobotStatus.msg`
| Field | Type | Description |
|---|---|---|
| `state` | `uint8` | `0=IDLE, 1=BUSY, 2=ERROR` |
| `position` | `uint8` | `0=RED_TOTE, 1=SCAN_TABLE` |

- **Published by:** `robot_mock`
- **Subscribed by:** `ScanTableManager`

### Services

#### `MoveRobot.srv`
| Direction | Field | Type | Description |
|---|---|---|---|
| Request | `target_position` | `uint8` | `0=RED_TOTE, 1=SCAN_TABLE` |
| Response | `success` | `bool` | |
| Response | `error_message` | `string` | |

- **Server:** `robot_mock` — **Client:** `ScanTableManager`

#### `MoveItem.srv`
| Direction | Field | Type | Description |
|---|---|---|---|
| Request | `target_position` | `uint8` | `0=RED_TOTE, 1=SCAN_TABLE, 2=POCKET, 3=REJECT_AREA` |
| Response | `success` | `bool` | |
| Response | `error_message` | `string` | |

- **Server:** `item_mock` — **Client:** `robot_mock`, `pusher_mock`

#### `SpawnItem.srv`
| Direction | Field | Type | Description |
|---|---|---|---|
| Request | *(empty)* | | |
| Response | `success` | `bool` | |
| Response | `item_id` | `uint8` | |
| Response | `error_message` | `string` | |

- **Server:** `item_mock` — **Client:** `ScanTableManager`

#### `TriggerScan.srv`
| Direction | Field | Type | Description |
|---|---|---|---|
| Request | *(empty)* | | |
| Response | `success` | `bool` | |
| Response | `barcodes` | `Barcode[]` | |
| Response | `error_message` | `string` | |

- **Server:** `scanner_mock` — **Client:** `ScanTableManager`

#### `Push.srv`
| Direction | Field | Type | Description |
|---|---|---|---|
| Request | `direction` | `uint8` | `0=POCKET, 1=REJECT` |
| Response | `success` | `bool` | |
| Response | `error_message` | `string` | |

- **Server:** `pusher_mock` — **Client:** `ScanTableManager`

### Shared Constants

| Constant | Values |
|---|---|
| Position | `RED_TOTE=0, SCAN_TABLE=1, POCKET=2, REJECT_AREA=3, UNKNOWN=4` |
| Push direction | `POCKET=0, REJECT=1` |
| Robot state | `IDLE=0, BUSY=1, ERROR=2` |

---

## Module: `item_mock`

**Package:** `hardware_simulation` (pure Python)

Manages virtual item lifecycle and state. Acts as ground truth for item position and barcode data.

| Role | Topic / Service | Type |
|---|---|---|
| Publishes | `/item/state` @ 10 Hz | `ItemState.msg` |
| Serves | `/item/spawn` | `SpawnItem.srv` |
| Serves | `/item/move` | `MoveItem.srv` |

**Business logic:**
- **SpawnItem:** Delete current item, generate new item in `RED_TOTE` with random 0–6 barcodes across random faces, random weight 1.0–5.0 kg. Return new `item_id`.
- **MoveItem:** Validate current item exists, update item position to `target_position`. Return success.
- Publishes full item state at 10 Hz for debug and mock consumption.
- No failure simulation — this is ground truth.

**Dependencies:** `scan_table_interfaces`

---

## Module: `robot_mock`

**Package:** `hardware_simulation`

Simulates the robot arm with two reachable positions.

| Role | Topic / Service | Type |
|---|---|---|
| Publishes | `/robot/status` @ 10 Hz | `RobotStatus.msg` |
| Serves | `/robot/move` | `MoveRobot.srv` |
| Calls | `/item/move` | `MoveItem.srv` |

**Business logic:**
- Maintains internal position (`RED_TOTE` or `SCAN_TABLE`) and state (`IDLE`, `BUSY`, `ERROR`).
- **MoveRobot:** Set `state=BUSY`, sleep 0.5 s to simulate motion, update internal position, set `state=IDLE`. Return success.
- When moving to `SCAN_TABLE`: calls `/item/move(target=SCAN_TABLE)` to relocate the item along with the robot.
- When moving to `RED_TOTE`: simply update local position — this is a return-to-default call, not a pick-and-place.
- Each service call has a **5% chance of random failure** (return `success=false`, state stays `IDLE`, position unchanged).
- Publishes status at 10 Hz.

**Dependencies:** `scan_table_interfaces`

---

## Module: `scanner_mock`

**Package:** `hardware_simulation`

Simulates 6 barcode scanners in triggered mode, one per item face.

| Role | Topic / Service | Type |
|---|---|---|
| Subscribes | `/item/state` | `ItemState.msg` |
| Serves | `/scanner/trigger` | `TriggerScan.srv` |

**Business logic:**
- **TriggerScan:** Read latest `ItemState`, verify item is at `SCAN_TABLE`. If not, return `success=false`.
- If item is on table: for each of the 6 faces, check if a barcode exists on that face. Return all found barcodes as a list.
- Each service call has a **5% chance of random failure** (simulates hardware malfunction).
- No deduplication — returns raw reads. Manager handles dedup.

**Dependencies:** `scan_table_interfaces`

---

## Module: `pusher_mock`

**Package:** `hardware_simulation`

Simulates the pusher mechanism.

| Role | Topic / Service | Type |
|---|---|---|
| Subscribes | `/item/state` | `ItemState.msg` |
| Serves | `/pusher/push` | `Push.srv` |
| Calls | `/item/move` | `MoveItem.srv` |

**Business logic:**
- **Push:** Verify item is at `SCAN_TABLE` via latest `ItemState`. If not, return `success=false`.
- If item is on table: call `/item/move` with `target=POCKET` or `REJECT_AREA` based on requested direction. Sleep 0.3 s to simulate actuation.
- Each service call has a **5% chance of random failure** (return `success=false`, item stays on table).

**Dependencies:** `scan_table_interfaces`

---

## Module: `table_sensor_mock`

**Package:** `hardware_simulation`

Simulates a weight/presence sensor on the scan table.

| Role | Topic / Service | Type |
|---|---|---|
| Subscribes | `/item/state` | `ItemState.msg` |
| Publishes | `/scan_table/occupancy` @ 10 Hz | `TableOccupancy.msg` |

**Business logic:**
- Reads latest `ItemState`. If `item.position == SCAN_TABLE`, publish `occupied=true` and weight from item. Otherwise `occupied=false`, `weight=0.0`.
- Pure passthrough from ground truth. No failure simulation — sensor is reliable by design.

**Dependencies:** `scan_table_interfaces`

---

## Module: `ScanTableManager`

**Package:** `scan_table_manager` (C++ node)

Central state machine orchestrating the entire scan table workflow.

| Role | Topic / Service | Type |
|---|---|---|
| Subscribes | `/scan_table/occupancy` | `TableOccupancy.msg` |
| Subscribes | `/robot/status` | `RobotStatus.msg` |
| Publishes | `/manager/state` @ 10 Hz | `ManagerState.msg` |
| Calls | `/robot/move` | `MoveRobot.srv` |
| Calls | `/item/spawn` | `SpawnItem.srv` |
| Calls | `/scanner/trigger` | `TriggerScan.srv` |
| Calls | `/pusher/push` | `Push.srv` |

**Internal state:**

| Field | Type | Description |
|---|---|---|
| `current_state` | enum | `INIT, PREPARE_ITEM, PICK_ITEM, VERIFY_ITEM_ON_TABLE, SCAN_ITEM, ITEM_MANAGEMENT, PUSH_ITEM_TO_POCKET, CHECK_TABLE_OCCUPIED, CLEAN_SCAN_TABLE, RECOVER_ROBOT, ERROR_RECOVERY` |
| `current_item_id` | `uint8` | |
| `current_barcodes` | `vector<Barcode>` | |
| `item_library` | `map<string, uint32>` | `barcode_id → count` |
| `latest_occupancy` | `TableOccupancy` | Cached from subscription |
| `last_transition` | `string` | e.g. `"PICK_ITEM → VERIFY_ITEM_ON_TABLE"` |
| `transition_reason` | `string` | e.g. `"MoveRobot success"` |

**Publishing logic:**
- A dedicated 10 Hz timer calls `publish_state()` independently of the 1 Hz state machine timer.
- Both timers run on the same single-threaded executor (`rclcpp::spin`), so no mutex is needed — callbacks are serialized.
- `publish_state()` assembles `ManagerState` from current internal fields and publishes to `/manager/state`.
- `last_transition` and `transition_reason` are updated inside `transition()` and the service-call callbacks whenever a state change occurs.

**Dependencies:** `scan_table_interfaces`

---

## Module: `scanning_process_monitor`

**Package:** `scanning_process_monitor` (Python node)

External read-only monitor. Subscribes to all relevant topics and renders a live terminal dashboard at 10 Hz using ANSI escape codes. Runs in its own terminal, independent of the other nodes.

| Role | Topic | Type |
|---|---|---|
| Subscribes | `/manager/state` | `ManagerState.msg` |
| Subscribes | `/robot/status` | `RobotStatus.msg` |
| Subscribes | `/item/state` | `ItemState.msg` |
| Subscribes | `/scan_table/occupancy` | `TableOccupancy.msg` |

**Internal state:**

| Field | Type |
|---|---|
| `latest_manager_state` | `ManagerState` |
| `latest_robot_status` | `RobotStatus` |
| `latest_item_state` | `ItemState` |
| `latest_occupancy` | `TableOccupancy` |
| `log_buffer` | `deque[str]`, max 10 entries (rolling log tail) |

**Display layout** (refreshed at 10 Hz):

```
┌── STATE MACHINE ────────────────────────────────────────────────────┐
│  All 11 states listed vertically as [ STATE_NAME ] boxes.           │
│  The active state is highlighted with ANSI inverse/bold/color.      │
│  All others are rendered dim.                                        │
└─────────────────────────────────────────────────────────────────────┘
┌── POSITIONS ────────────────────────────────────────────────────────┐
│  ROBOT:  [ RED_TOTE ] [ SCAN_TABLE ]                                │
│  ITEM:   [ RED_TOTE ] [ SCAN_TABLE ] [ POCKET ] [ REJECT ] [ UNK ] │
│  Active position highlighted; others dim.                            │
└─────────────────────────────────────────────────────────────────────┘
┌── STATUS ───────────────────────────────────────────────────────────┐
│  TABLE:  occupied=true   weight=2.30 kg                             │
│  ROBOT:  state=IDLE      item_library_size=7                        │
└─────────────────────────────────────────────────────────────────────┘
┌── LOG (last 10 entries) ────────────────────────────────────────────┐
│  [HH:MM:SS.mmm]  PICK_ITEM → VERIFY_ITEM_ON_TABLE  (MoveRobot ok)  │
│  [HH:MM:SS.mmm]  TABLE occupied=true, weight=2.30 kg               │
│  ...                                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

**Rendering logic:**
- A 10 Hz wall timer fires `render()`. It calls `print('\033[2J\033[H', end='')` to clear the terminal, then prints all four panels.
- Each subscription callback updates only its cached field and appends a line to `log_buffer` (truncating to max 10). No rendering in callbacks.
- Rendering is decoupled from message arrival — the display always shows the freshest cached values.

**Dependencies:** `scan_table_interfaces`

---

## Launch

**Package:** `robot_scanner_bringup`

Two launch files are used:

### 1. `scan_table_manager/launch/scan_table_manager.launch.py`
Launches `ScanTableManager` node only.

### 2. `robot_scanner_bringup/launch/bringup.launch.py` *(top-level entry point)*
- Includes `scan_table_manager.launch.py`
- Launches all hardware simulation nodes: `item_mock`, `robot_mock`, `scanner_mock`, `pusher_mock`, `table_sensor_mock`

```bash
ros2 launch robot_scanner_bringup bringup.launch.py
```

> **Note:** `ScanningProcessMonitor` is **not** part of the main launch file. Run it separately in its own terminal:
> ```bash
> ros2 run scanning_process_monitor monitor
> ```

---

## Dependency Graph

```
scan_table_interfaces
  ├── hardware_simulation
  │     ├── item_mock
  │     ├── robot_mock
  │     ├── scanner_mock
  │     ├── pusher_mock
  │     └── table_sensor_mock
  ├── scan_table_manager
  │     └── ScanTableManager
  ├── scanning_process_monitor  (read-only observer)
  │     └── ScanningProcessMonitor
  └── robot_scanner_bringup  (top-level launch package)
        └── bringup.launch.py → includes scan_table_manager.launch.py + hardware_simulation nodes
```

---

## Communication Map

```
ScanTableManager
  ├── calls /robot/move                → robot_mock
  ├── calls /item/spawn                → item_mock
  ├── calls /scanner/trigger           → scanner_mock
  ├── calls /pusher/push               → pusher_mock
  ├── subscribes /scan_table/occupancy ← table_sensor_mock
  ├── subscribes /robot/status         ← robot_mock
  └── publishes  /manager/state        → ScanningProcessMonitor

robot_mock
  └── calls /item/move                 → item_mock

pusher_mock
  └── calls /item/move                 → item_mock

scanner_mock
  └── subscribes /item/state           ← item_mock

table_sensor_mock
  └── subscribes /item/state           ← item_mock

ScanningProcessMonitor  (read-only, no services, no outgoing topics)
  ├── subscribes /manager/state        ← ScanTableManager
  ├── subscribes /robot/status         ← robot_mock
  ├── subscribes /item/state           ← item_mock
  └── subscribes /scan_table/occupancy ← table_sensor_mock
```
