sudo systemctl stop watches_server
sudo systemctl stop watches_sensor
sudo systemctl stop watches_controller

sudo systemctl disable watches_server
sudo systemctl disable watches_sensor
sudo systemctl disable watches_controller

sudo rm /etc/systemd/system/watches_server.service
sudo rm /etc/systemd/system/watches_sensor.service
sudo rm /etc/systemd/system/watches_controller.service

sudo systemctl daemon-reload
sudo systemctl reset-failed
