import random
import time

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from scan_table_interfaces.msg import RobotStatus
from scan_table_interfaces.srv import MoveItem, MoveRobot

# Position constants
RED_TOTE = 0
SCAN_TABLE = 1

# State constants
IDLE = 0
BUSY = 1
ERROR = 2

FAILURE_RATE = 0.05


class RobotMock(Node):

    def __init__(self):
        super().__init__('robot_mock')

        self._position: int = RED_TOTE
        self._state: int = IDLE

        cb_group = ReentrantCallbackGroup()

        self._status_pub = self.create_publisher(RobotStatus, '/robot/status', 10)
        self._move_srv = self.create_service(
            MoveRobot, '/robot/move', self._handle_move, callback_group=cb_group)

        self._item_move_client = self.create_client(
            MoveItem, '/item/move', callback_group=cb_group)

        self.create_timer(0.2, self._publish_status)  # 5 Hz

        self.get_logger().info('robot_mock started')

    def _publish_status(self):
        msg = RobotStatus()
        msg.state = self._state
        msg.position = self._position
        self._status_pub.publish(msg)

    def _handle_move(self, request, response):
        target = request.target_position

        if target not in (RED_TOTE, SCAN_TABLE):
            response.success = False
            response.error_message = f'Invalid target position: {target}'
            return response

        if random.random() < FAILURE_RATE:
            response.success = False
            response.error_message = 'Random hardware failure'
            self.get_logger().warn('MoveRobot: random failure triggered')
            return response

        self._state = BUSY
        time.sleep(0.5)  # simulate motion

        if target == SCAN_TABLE:
            item_success, item_error = self._call_item_move(SCAN_TABLE)
            if not item_success:
                self._state = IDLE
                response.success = False
                response.error_message = f'Failed to move item: {item_error}'
                return response

        self._position = target
        self._state = IDLE

        response.success = True
        response.error_message = ''
        self.get_logger().info(f'Robot moved to position {target}')
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
    node = RobotMock()
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
