#! /usr/bin/bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3-pip
sudo apt install --upgrade python3-setuptools
sudo apt install python3-venv
python3 -m venv .env --system-site-packages
#We need to work as root since we are working with TUN
#source .env/bin/activate
sudo pip3 install --upgrade adafruit-python-shell --break-system-packages

if ! [ -f ./raspi-blinka.py]; then
	echo "Downloading Raspi Blinka drivers"
	wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
fi

sudo PATH=$PATH python3 raspi-blinka.py
dtoverlay=spi1-3cs
sudo pip3 install -r requirements.txt --break-system-packages
clear
sudo PATH=$PATH python3 pyg.py
# Commented out since we use modified drivers
# pip3 install circuitpython-nrf24l01
# cd internet_inside
# git clone https://github.com/2bndy5/CircuitPython_nRF24L01.git
# cd CircuitPython_nRF24L01/examples
# python3 nrf24l01_simple_test.py
