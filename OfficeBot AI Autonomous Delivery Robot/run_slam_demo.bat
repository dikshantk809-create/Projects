@echo off
title OfficeBot - SLAM Mapping Demo
echo Launching OfficeBot SLAM demo (Gazebo + slam_toolbox + RViz)...
echo A Gazebo 3D window and RViz will open - please wait ~20s for them to load.
echo Then the robot will auto-drive to build the map (about 1 minute).
echo.
wsl -d Ubuntu-24.04 -- bash -c "tr -d '\r' < /mnt/c/Users/HP/slam_demo.sh > /tmp/slam_demo.sh && bash /tmp/slam_demo.sh"
echo.
echo ====== window stays open ======
pause
