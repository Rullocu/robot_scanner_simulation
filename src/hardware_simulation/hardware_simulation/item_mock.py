import rclpy
from rclpy.node import Node

from scan_table_interfaces.msg import Barcode, ItemState
from scan_table_interfaces.srv import MoveItem, SpawnItem

# Position constants
RED_TOTE = 0
SCAN_TABLE = 1
POCKET = 2
REJECT_AREA = 3
UNKNOWN = 4

FIXED_WEIGHT = 2.0


def _make_barcode(barcode_id: str, face: int) -> Barcode:
    b = Barcode()
    b.barcode_id = barcode_id
    b.face = face
    return b


# Predefined item list (cycled in order on each SpawnItem call).
# Each entry is a list of (barcode_id, face) tuples.
ITEM_DEFINITIONS: list[tuple[str, list[tuple[str, int]]]] = [
    # Slot 1: two identical barcodes on two different faces
    ('two-faces',    [('AAAA1111', 0), ('AAAA1111', 1)]),
    # Slot 2: two identical barcodes on the same face
    ('same-face',    [('BBBB2222', 2), ('BBBB2222', 2)]),
    # Slot 3: no barcodes
    ('no-barcode',   []),
    # Slot 4: six identical barcodes, one per face
    ('full-scan',    [(('CCCC3333'), f) for f in range(6)]),
    # Slot 5: conflicting barcodes — two different IDs across faces
    ('conflicting',  [('DDDD4444', 0), ('DDDD4444', 1),
                      ('EEEE5555', 2), ('EEEE5555', 3)]),
]


class ItemMock(Node):

    def __init__(self):
        super().__init__('item_mock')

        self._slot_index: int = 0  # next slot to spawn (0-based, wraps at len)
        self._item_id: int = 0
        self._position: int = UNKNOWN
        self._barcodes: list[Barcode] = []
        self._item_exists: bool = False

        self._state_pub = self.create_publisher(ItemState, '/item/state', 10)
        self._spawn_srv = self.create_service(SpawnItem, '/item/spawn', self._handle_spawn)
        self._move_srv = self.create_service(MoveItem, '/item/move', self._handle_move)

        self.create_timer(0.1, self._publish_state)  # 10 Hz

        self.get_logger().info('item_mock started')

    def _publish_state(self):
        msg = ItemState()
        msg.item_id = self._item_id
        msg.position = self._position if self._item_exists else UNKNOWN
        msg.weight = FIXED_WEIGHT if self._item_exists else 0.0
        msg.barcodes = list(self._barcodes)
        self._state_pub.publish(msg)

    def _handle_spawn(self, _request, response):
        label, barcode_defs = ITEM_DEFINITIONS[self._slot_index]
        self._item_id = self._slot_index + 1  # item IDs: 1–5, tied to slot
        self._slot_index = (self._slot_index + 1) % len(ITEM_DEFINITIONS)

        self._position = RED_TOTE
        self._barcodes = [_make_barcode(bid, face) for bid, face in barcode_defs]
        self._item_exists = True

        response.success = True
        response.item_id = self._item_id
        response.error_message = ''
        self.get_logger().info(
            f'Spawned item {self._item_id} (slot: {label}) '
            f'with {len(self._barcodes)} barcodes, weight={FIXED_WEIGHT} kg'
        )
        return response

    def _handle_move(self, request, response):
        if not self._item_exists:
            response.success = False
            response.error_message = 'No item exists'
            return response

        target = request.target_position
        if target not in (RED_TOTE, SCAN_TABLE, POCKET, REJECT_AREA):
            response.success = False
            response.error_message = f'Invalid target position: {target}'
            return response

        self._position = target
        response.success = True
        response.error_message = ''
        self.get_logger().info(f'Item {self._item_id} moved to position {target}')
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ItemMock()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
