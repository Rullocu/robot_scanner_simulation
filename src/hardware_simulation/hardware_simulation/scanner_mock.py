import random

import rclpy
from rclpy.node import Node

from scan_table_interfaces.msg import ItemState
from scan_table_interfaces.srv import TriggerScan

# Position constants
SCAN_TABLE = 1

FAILURE_RATE = 0.05


class ScannerMock(Node):

    def __init__(self):
        super().__init__('scanner_mock')

        self._latest_item_state: ItemState | None = None

        self._item_state_sub = self.create_subscription(
            ItemState, '/item/state', self._on_item_state, 10)
        self._trigger_srv = self.create_service(
            TriggerScan, '/scanner/trigger', self._handle_trigger)

        self.get_logger().info('scanner_mock started')

    def _on_item_state(self, msg: ItemState):
        self._latest_item_state = msg

    def _handle_trigger(self, request, response):
        if random.random() < FAILURE_RATE:
            response.success = False
            response.error_message = 'Random hardware failure'
            self.get_logger().warn('TriggerScan: random failure triggered')
            return response

        if self._latest_item_state is None:
            response.success = False
            response.error_message = 'No item state received yet'
            return response

        if self._latest_item_state.position != SCAN_TABLE:
            response.success = False
            response.error_message = 'Item is not on scan table'
            return response

        response.success = True
        response.barcodes = list(self._latest_item_state.barcodes)
        response.error_message = ''
        self.get_logger().info(f'Scan complete: {len(response.barcodes)} barcodes found')
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ScannerMock()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
