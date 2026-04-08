import rclpy
from rclpy.node import Node

from scan_table_interfaces.msg import ItemState, TableOccupancy

SCAN_TABLE = 1


class TableSensorMock(Node):

    def __init__(self):
        super().__init__('table_sensor_mock')

        self._latest_item_state: ItemState | None = None

        self._item_state_sub = self.create_subscription(
            ItemState, '/item/state', self._item_state_callback, 10
        )
        self._occupancy_pub = self.create_publisher(TableOccupancy, '/scan_table/occupancy', 10)

        self.create_timer(0.2, self._publish_occupancy)  # 5 Hz

        self.get_logger().info('table_sensor_mock started')

    def _item_state_callback(self, msg: ItemState):
        self._latest_item_state = msg

    def _publish_occupancy(self):
        msg = TableOccupancy()
        if self._latest_item_state is not None and self._latest_item_state.position == SCAN_TABLE:
            msg.occupied = True
            msg.weight = self._latest_item_state.weight
        else:
            msg.occupied = False
            msg.weight = 0.0
        self._occupancy_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TableSensorMock()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
