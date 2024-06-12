# Pin Assignment:
## nRF24L01+(0):

VCC:01

GND:06

CE:15(GPIO22)

CSN:24(GPIO7)

SCK:23(GPIO11)

MOSI:19(GPIO10)

MISO:21(GPIO09)

## nRF24L01+(1):

VCC:17

GND:09

CE:18(GPIO24)

CSN:32(GPIO12) should be 36(GPIO16)

SCK:40(GPIO21)

MOSI:38(GPIO20)

MISO:35(GPIO19)

# How to run
1. Run the automation script to set up the environment correctly, this will setup a virtual environment and activate it.
2. Figure out which of the PIs should be base and which should be mobile
3. Set the correct IP addresses for control web server and the LongG interface addresses in `pyg/application.py`. Specifically: make sure to set `MOBILE_IP`, `BASE_IP`, `CONTROL_SERVER_IP`, `CONTROL_SERVER_PORT` to what you expect them to be.
4. Make sure the control server is running `pyg/control_webserver.py`
5. Run `pyg/application.py` on both PIs. Start the base before the mobile.
6. Success!