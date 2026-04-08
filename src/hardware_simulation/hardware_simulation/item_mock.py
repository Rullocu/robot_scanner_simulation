import random
import uuid

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


class ItemMock(Node):

    def __init__(self):
        super().__init__('item_mock')

        self._item_id: int = 0
        self._position: int = UNKNOWN
        self._weight: float = 0.0
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
        msg.weight = self._weight if self._item_exists else 0.0
        msg.barcodes = list(self._barcodes)
        self._state_pub.publish(msg)

    def _handle_spawn(self, request, response):
        self._item_id = (self._item_id % 255) + 1
        self._position = RED_TOTE
        self._weight = round(random.uniform(1.0, 5.0), 2)
        self._barcodes = self._generate_barcodes()
        self._item_exists = True

        response.success = True
        response.item_id = self._item_id
        response.error_message = ''
        self.get_logger().info(
            f'Spawned item {self._item_id} with {len(self._barcodes)} barcodes, '
            f'weight={self._weight} kg'
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

    def _generate_barcodes(self) -> list[Barcode]:
        num_faces = random.randint(0, 6)
        faces = random.sample(range(6), num_faces)
        shared_id = str(uuid.uuid4())[:8]
        barcodes = []
        for face in faces:
            b = Barcode()
            b.barcode_id = shared_id
            b.face = face
            barcodes.append(b)
        return barcodes


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
