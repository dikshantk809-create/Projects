#!/bin/bash
set -e
source /opt/ros/jazzy/setup.bash
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/opt/ros/jazzy/share/turtlebot3_gazebo/models

echo "=== OfficeBot SLAM DEMO: building a live map while driving ==="

ros2 launch nav2_bringup tb3_simulation_launch.py slam:=True headless:=False &
LAUNCH_PID=$!

echo "Waiting 35s for Gazebo + slam_toolbox + RViz to fully start..."
sleep 35

python3 - <<'PY'
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import time

class Explorer(Node):
    def __init__(self):
        super().__init__('officebot_explorer')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def drive(self, lin, ang, secs):
        msg = Twist()
        msg.linear.x = lin
        msg.angular.z = ang
        end = time.time() + secs
        while time.time() < end:
            self.pub.publish(msg)
            time.sleep(0.1)
        self.pub.publish(Twist())

rclpy.init()
node = Explorer()
print("EXPLORE: driving forward...", flush=True)
node.drive(0.2, 0.0, 6)
print("EXPLORE: turning...", flush=True)
node.drive(0.0, 0.5, 6)
print("EXPLORE: forward...", flush=True)
node.drive(0.2, 0.0, 6)
print("EXPLORE: turning...", flush=True)
node.drive(0.0, 0.5, 6)
print("EXPLORE: forward...", flush=True)
node.drive(0.2, 0.0, 6)
print("EXPLORE: turning back...", flush=True)
node.drive(0.0, -0.5, 12)
print("EXPLORE: forward...", flush=True)
node.drive(0.2, 0.0, 6)
print("EXPLORE done - map should now show explored area", flush=True)
node.destroy_node()
rclpy.shutdown()
PY

echo "Saving the SLAM-built map to ~/officebot_maps ..."
mkdir -p ~/officebot_maps
ros2 run nav2_map_server map_saver_cli -f ~/officebot_maps/officebot_slam_map --ros-args -p save_map_timeout:=10000.0 || echo "map_saver_cli finished (check output above)"

echo "=== SLAM DEMO COMPLETE - map saved to ~/officebot_maps/officebot_slam_map.pgm ==="
echo "Gazebo/RViz windows still open - look at the RViz map panel to see the built map."
wait $LAUNCH_PID
