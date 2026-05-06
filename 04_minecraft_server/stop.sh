#!/bin/bash

SERVICE_NAME="minecraft.service"

echo "Stopping Minecraft server..."
sudo systemctl stop "$SERVICE_NAME"
echo "Minecraft server stop requested."
