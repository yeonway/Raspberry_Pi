@echo off
cd /d %~dp0

java -Xms1G -Xmx4G -jar paper.jar nogui

pause
