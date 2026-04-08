import random
import time

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from scan_table_interfaces.msg import ItemState
from scan_table_interfaces.srv import MoveItem, Push

# Position constants
SCAN_TABLE = 1
POCKET = 2
REJECT_AREA = 3

# Push direction constants
DIRECTION_POCKET = 0
DIRECTION_REJECT = 1

FAILURE_RATE = 0.05


class PusherMock(Node):

    def __init__(self):
        super().__init__('pusher_mock')

        self._latest_item_state: ItemState | None = None

        cb_group = ReentrantCallbackGroup()

        self._item_state_sub = self.create_subscription(
            ItemState, '/item/state', self._on_item_state, 10)
        self._push_srv = self.create_service(
            Push, '/pusher/push', self._handle_push, callback_group=cb_group)
        self._item_move_client = self.create_client(
            MoveItem, '/item/move', callback_group=cb_group)

        self.get_logger().info('pusher_mock started')

    def _on_item_state(self, msg: ItemState):
        self._latest_item_state = msg

    def _handle_push(self, request, response):
        if random.random() < FAILURE_RATE:
            response.success = False
            response.error_message = 'Random hardware failure'
            self.get_logger().warn('Push: random failure triggered')
            return response

        if self._latest_item_state is None:
            response.success = False
            response.error_message = 'No item state received yet'
            return response

        if self._latest_item_state.position != SCAN_TABLE:
            response.success = False
            response.error_message = 'Item is not on scan table'
            return response

        if request.direction == DIRECTION_POCKET:
            target = POCKET
        elif request.direction == DIRECTION_REJECT:
            target = REJECT_AREA
        else:
            response.success = False
            response.error_message = f'Invalid push direction: {request.direction}'
            return response

        item_success, item_error = self._call_item_move(target)
        if not item_success:
            response.success = False
            response.error_message = f'Failed to move item: {item_error}'
            return response

        time.sleep(0.3)  # simulate actuation

        response.success = True
        response.error_message = ''
        self.get_logger().info(f'Item pushed to position {target}')
        return response

    def _call_item_move(self, target_position: int):
        if not self._item_move_client.wait_for_service(timeout_sec=2.0):
            return False, '/item/move service not available'

        req = MoveItem.Request()
        req.target_position = target_position

        future = self._item_move_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result() is None:
            return False, 'Service call timed out'

        result = future.result()
        return result.success, result.error_message


def main(args=None):
    rclpy.init(args=args)
    node = PusherMock()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
