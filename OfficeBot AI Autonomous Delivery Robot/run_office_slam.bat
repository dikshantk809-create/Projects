@echo off
title OfficeBot - Custom Office World + SLAM
echo Launching OfficeBot's own 15-desk office world in Gazebo, with SLAM + RViz...
echo A Gazebo 3D window and RViz will open - please wait ~20-30s for them to load.
echo Then the robot will auto-drive through the office to build the map (about 1.5 minutes).
echo.
wsl -d Ubuntu-24.04 -- bash -c "tr -d '\r' < /mnt/c/Users/HP/deploy_office_slam.sh > /tmp/deploy_office_slam.sh && bash /tmp/deploy_office_slam.sh"
echo.
echo ====== window stays open ======
pause
