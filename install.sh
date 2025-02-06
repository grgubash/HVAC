sudo cp services/watches-server.service /etc/systemd/system
sudo cp services/watches-sensor.service /etc/systemd/system
sudo cp services/watches-controller.service /etc/systemd/system

sudo systemctl daemon-reload

sudo systemctl enable watches-server
sudo systemctl enable watches-sensor
sudo systemctl enable watches-controller

sudo systemctl start watches-server
sudo systemctl start watches-sensor
sudo systemctl start watches-controller
