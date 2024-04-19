#! /usr/bin/bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3-pip
sudo apt install --upgrade python3-setuptools
sudo apt install python3-venv
mkdir internet_inside && cd internet_inside
python3 -m venv env --system-site-packages
source env/bin/activate
cd ~
pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
sudo -E env PATH=$PATH python3 raspi-blinka.py
dtoverlay=spi1-3cs
pip3 install circuitpython-nrf24l01
cd internet_inside
git clone https://github.com/2bndy5/CircuitPython_nRF24L01.git
cd CircuitPython_nRF24L01/examples
python3 nrf24l01_simple_test.py
