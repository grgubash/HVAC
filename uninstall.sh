sudo systemctl stop watches-server
sudo systemctl stop watches-sensor
sudo systemctl stop watches-controller

sudo systemctl disable watches-server
sudo systemctl disable watches-sensor
sudo systemctl disable watches-controller

sudo rm /etc/systemd/system/watches-server.service
sudo rm /etc/systemd/system/watches-sensor.service
sudo rm /etc/systemd/system/watches-controller.service

sudo systemctl daemon-reload
sudo systemctl reset-failed
