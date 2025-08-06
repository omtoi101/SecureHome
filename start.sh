#!/bin/bash

# Load the v4l2loopback module
echo "Loading v4l2loopback module..."
modprobe v4l2loopback

# Start the main application components
echo "Starting application..."
python3 run.py &
python3 main.py &
python3 bot.py &

# Wait for all background processes to finish
wait
