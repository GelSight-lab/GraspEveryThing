#! /bin/bash

sudo apt-get update
sudo apt-get install python3-flask python3-pyaudio
sudo cp run_imaging.service /lib/systemd/system/run_imaging.service
sudo systemctl daemon-reload
sudo systemctl enable run_imaging.service
sudo systemctl start run_imaging.service
echo "Service installed and started. Check status with 'sudo systemctl status run_imaging.service'"