@echo off
title OfficeBot - Nav2 REAL Office v2
echo Cleaning up old processes and launching FULL Nav2 autonomy in OfficeBot's real 15-desk office...
echo A Gazebo 3D window and RViz will open - please wait ~30-40s for them to load.
echo Nav2 will then send the robot to real desks and back to the dock, autonomously.
echo.
wsl -d Ubuntu-24.04 -- bash -c "tr -d '\r' < /mnt/c/Users/HP/nav_office_v2.sh > /tmp/nav_office_v2.sh && bash /tmp/nav_office_v2.sh"
echo.
echo ====== window stays open ======
pause
