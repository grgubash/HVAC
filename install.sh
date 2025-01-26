sudo cp services/server.service /etc/systemd/system
sudo cp services/sensor.service /etc/systemd/system
sudo cp services/controller.service /etc/systemd/system

sudo systemctl -daemon-reload

sudo systemctl enable server
sudo systemctl enable sensor
sudo systemctl enable controller

sudo systemctl start server
sudo systemctl start sensor
sudo systemctl start controller