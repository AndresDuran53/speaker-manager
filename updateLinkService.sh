#!/bin/bash
sudo systemctl stop speakerManager.service
sudo systemctl disable speakerManager.service
sudo rm /etc/systemd/system/speakerManager.service
sudo cp speakerManager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable speakerManager.service
sudo systemctl start speakerManager.service
