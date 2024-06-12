#! /usr/bin/bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3-pip
sudo apt install --upgrade python3-setuptools
sudo apt install python3-venv
python3 -m venv .env --system-site-packages
#We need to work as root since we are working with TUN
sudo ./env/bin/pip3 install --upgrade adafruit-python-shell

if ! [ -f ./raspi-blinka.py]; then
	echo "Downloading Raspi Blinka drivers"
	wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
fi

sudo .env/bin/python3 raspi-blinka.py
dtoverlay=spi1-3cs
sudo .env/bin/pip3 install -r requirements.txt
cd pyg_control_system
maturin develop
cd ..
source .env/bin/activate
clear
