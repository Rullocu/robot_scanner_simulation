import sys
from collections import deque
from datetime import datetime

import rclpy
from rclpy.node import Node

from scan_table_interfaces.msg import ItemState
from scan_table_interfaces.msg import ManagerState
from scan_table_interfaces.msg import RobotStatus
from scan_table_interfaces.msg import TableOccupancy

# ── ANSI helpers ──────────────────────────────────────────────────────────────
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
BG_GREEN = '\033[42;30m'   # green background, black text  → active / normal
BG_RED = '\033[41;97m'     # red background, white text    → ERROR_RECOVERY active
BG_YELLOW = '\033[43;30m'  # yellow background, black text → BUSY robot

# ── domain constants ──────────────────────────────────────────────────────────
# Order must match the C++ State enum
ALL_STATES = [
    'INIT',
    'CHECK_TABLE_OCCUPIED',
    'CLEAN_SCAN_TABLE',
    'RECOVER_ROBOT',
    'PREPARE_ITEM',
    'PICK_ITEM',
    'VERIFY_ITEM_ON_TABLE',
    'SCAN_ITEM',
    'ITEM_MANAGEMENT',
    'PUSH_ITEM_TO_POCKET',
    'ERROR_RECOVERY',
]

# Two-column layout: main flow (left) | side branches (right)
LEFT_STATES = [
    'INIT',
    'CHECK_TABLE_OCCUPIED',
    'RECOVER_ROBOT',
    'PREPARE_ITEM',
    'PICK_ITEM',
    'VERIFY_ITEM_ON_TABLE',
    'SCAN_ITEM',
    'ITEM_MANAGEMENT',
    'PUSH_ITEM_TO_POCKET',
]
RIGHT_STATES = [
    'CLEAN_SCAN_TABLE',
    'ERROR_RECOVERY',
]

ROBOT_POSITIONS = ['RED_TOTE', 'SCAN_TABLE']
ITEM_POSITIONS = ['RED_TOTE', 'SCAN_TABLE', 'POCKET', 'REJECT_AREA', 'UNKNOWN']
ROBOT_STATES = ['IDLE', 'BUSY', 'ERROR']

SEP = '─' * 74
STATE_BOX_WIDTH = 24   # fixed inner label width keeps columns stable


# ── node ──────────────────────────────────────────────────────────────────────
class MonitorNode(Node):

    def __init__(self):
        super().__init__('scanning_process_monitor')

        self._manager_state = None
        self._robot_status = None
        self._item_state = None
        self._occupancy = None
        self._log: deque = deque(maxlen=10)   # newest first

        self.create_subscription(
            ManagerState, '/manager/state', self._on_manager_state, 10)
        self.create_subscription(
            RobotStatus, '/robot/status', self._on_robot_status, 10)
        self.create_subscription(
            ItemState, '/item/state', self._on_item_state, 10)
        self.create_subscription(
            TableOccupancy, '/scan_table/occupancy', self._on_occupancy, 10)

        self.create_timer(0.1, self._render)   # 10 Hz

    # ── subscription callbacks ─────────────────────────────────────────────
    def _on_manager_state(self, msg: ManagerState):
        prev = self._manager_state
        self._manager_state = msg
        # append to log only when a new transition has occurred
        if prev is None or prev.last_transition != msg.last_transition:
            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            self._log.appendleft(
                f'[{ts}]  {msg.last_transition}  ({msg.transition_reason})'
            )

    def _on_robot_status(self, msg: RobotStatus):
        self._robot_status = msg

    def _on_item_state(self, msg: ItemState):
        self._item_state = msg

    def _on_occupancy(self, msg: TableOccupancy):
        self._occupancy = msg

    # ── render ─────────────────────────────────────────────────────────────
    def _render(self):
        now = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        current_state = self._manager_state.state if self._manager_state else None

        lines = []

        # ── header ──────────────────────────────────────────────────────────
        lines.append(SEP)
        title = 'SCAN TABLE PROCESS MONITOR'
        lines.append(f'  {BOLD}{title}{RESET}{"  " + now:>{len(SEP) - len(title) - 2}}')
        lines.append(SEP)

        # ── state machine ────────────────────────────────────────────────────
        lines.append(f'  {BOLD}STATE MACHINE{RESET}')
        lines.append('')
        for i, left_name in enumerate(LEFT_STATES):
            left_idx = ALL_STATES.index(left_name)
            left_box = self._state_box(left_name, left_idx == current_state)

            right_box = ''
            if i < len(RIGHT_STATES):
                right_name = RIGHT_STATES[i]
                right_idx = ALL_STATES.index(right_name)
                right_box = '    ' + self._state_box(right_name, right_idx == current_state)

            lines.append(f'  {left_box}{right_box}')

        lines.append('')
        lines.append(SEP)

        # ── positions ────────────────────────────────────────────────────────
        lines.append(f'  {BOLD}POSITIONS{RESET}')
        lines.append('')

        robot_pos = self._robot_status.position if self._robot_status else None
        robot_row = '  '.join(
            self._pos_box(name, i == robot_pos)
            for i, name in enumerate(ROBOT_POSITIONS)
        )
        lines.append(f'  Robot : {robot_row}')

        item_pos = self._item_state.position if self._item_state else None
        item_row = '  '.join(
            self._pos_box(name, i == item_pos)
            for i, name in enumerate(ITEM_POSITIONS)
        )
        lines.append(f'  Item  : {item_row}')

        lines.append('')
        lines.append(SEP)

        # ── status ───────────────────────────────────────────────────────────
        lines.append(f'  {BOLD}STATUS{RESET}')
        lines.append('')

        if self._occupancy:
            occ = self._occupancy
            occ_flag = f'{BOLD}YES{RESET}' if occ.occupied else 'no '
            lines.append(f'  Table : occupied={occ_flag}   weight={occ.weight:.2f} kg')
        else:
            lines.append('  Table : (waiting...)')

        if self._robot_status:
            rs = self._robot_status
            rs_name = ROBOT_STATES[rs.state] if rs.state < len(ROBOT_STATES) else '?'
            rp_name = ROBOT_POSITIONS[rs.position] if rs.position < len(ROBOT_POSITIONS) else '?'
            rs_colored = f'{BG_YELLOW} {rs_name} {RESET}' if rs.state == 1 else rs_name
            lines.append(f'  Robot : state={rs_colored}   pos={rp_name}')
        else:
            lines.append('  Robot : (waiting...)')

        if self._manager_state:
            ms = self._manager_state
            lines.append(
                f'  Item  : id={ms.current_item_id}   '
                f'library={ms.item_library_size} unique barcode(s)'
            )
        else:
            lines.append('  Item  : (waiting...)')

        if self._manager_state and self._manager_state.last_transition:
            ms = self._manager_state
            lines.append('')
            lines.append(f'  Last  : {ms.last_transition}')
            lines.append(f'  Why   : {ms.transition_reason}')

        lines.append('')
        lines.append(SEP)

        # ── log ──────────────────────────────────────────────────────────────
        lines.append(f'  {BOLD}LOG{RESET}  (last 10 transitions, newest first)')
        lines.append('')
        if self._log:
            for entry in self._log:
                lines.append(f'  {entry}')
        else:
            lines.append('  (waiting for first transition...)')
        lines.append(SEP)

        # clear terminal and print
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.write('\n'.join(lines) + '\n')
        sys.stdout.flush()

    # ── box helpers ──────────────────────────────────────────────────────────
    def _state_box(self, name: str, active: bool) -> str:
        label = name[:STATE_BOX_WIDTH].ljust(STATE_BOX_WIDTH)
        if active:
            color = BG_RED if name == 'ERROR_RECOVERY' else BG_GREEN
            return f'{color}[{label}]{RESET}'
        return f'{DIM}[{label}]{RESET}'

    def _pos_box(self, name: str, active: bool) -> str:
        if active:
            return f'{BG_GREEN}[{name}]{RESET}'
        return f'{DIM}[{name}]{RESET}'


# ── entry point ───────────────────────────────────────────────────────────────
def main(args=None):
    rclpy.init(args=args)
    node = MonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        # restore terminal on exit
        sys.stdout.write(RESET + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
