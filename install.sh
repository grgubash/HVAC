sudo cp services/watches_server.service /etc/systemd/system
sudo cp services/watches_sensor.service /etc/systemd/system
sudo cp services/watches_controller.service /etc/systemd/system

sudo systemctl daemon-reload

sudo systemctl enable watches_server
sudo systemctl enable watches_sensor
sudo systemctl enable watches_controller

sudo systemctl start watches_server
sudo systemctl start watches_ sensor
sudo systemctl start watches_controller
