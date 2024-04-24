import struct
import board
from digitalio import DigitalInOut
from rf24 import RF24
import spidev
import subprocess
import threading
import time
from tuntap import TunTap

# Define tun device
tun = TunTap(nic_type="Tun", nic_name="LongG")


cond_in = threading.Condition()
tun_in_queue = []

cond_out = threading.Condition()
tun_out_queue = []

# define Radios
#rf_rx = RF24(None, None, None, None, None)
#nrf_tx = RF24(None, None, None, None, None)

# invalid default values for scoping
SPI_BUS, CSN_PIN, CE_PIN = (None, None, None)

# Constants for CE & CSN pins for the two SPI buses
CE_BUS_0 = board.D22
CE_BUS_1 = board.D24
CSN_BUS_0 = 0
CSN_BUS_1 = 10

# We only use device 0 for the two SPI buses
SPI_DEV = 0

#Radio Parameters
POWER_LEVEL = -12 #DBM
DELAY = 15 #e-15
COUNT = 5
DATA_RATE = 2 #MBps
CRC_LENGTH = 8 #Bytes

#Fragments size
FRAG_SIZE = 30


# Setup the two radios
def setup(role) -> (RF24, RF24):
    # configure tun device
    if role == 1:
        # Node
        tun.config(ip="192.168.1.2", mask="255.255.255.0")

        command = 'ip route add 8.8.8.8 via 192.168.1.1 dev LongG'
        subprocess.run(command, shell=True)


    if role == 0:
        # Base
        tun.config(ip="192.168.1.1", mask="255.255.255.0")
        subprocess.run('iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE', shell=True)
        command = 'sudo iptables -A FORWARD -i eth0 -o LongG -m state --state RELATED,ESTABLISHED -j ACCEPT'
        subprocess.run(command,shell=True)
        subprocess.run('sudo iptables -A FORWARD -i LongG -o eth0 -j ACCEPT', shell=True)


    # Create SPI bus object
    SPI_BUS_RX = spidev.SpiDev()  # for a faster interface on linux
    SPI_BUS_TX = spidev.SpiDev()

    # On Linux, csn value is a bit coded
    #                 0 = bus 0, CE0 - /dev/spidev0.0, SpiDev 0  
    #                10 = bus 1, CE0 - /dev/spidev1.0, SpiDev 1
    # Radio 0
    CE_PIN_0 = DigitalInOut(board.D22)
    CSN_PIN_0 = CSN_BUS_0
    SPI_BUS_NUM_0 = 0
    # Radio 1
    CE_PIN_1 = DigitalInOut(board.D24)
    CSN_PIN_1 = CSN_BUS_1 
    SPI_BUS_NUM_1 = 1

    # initialize the nRF24L01 on the spi bus object with the specified CE & CSN pin,
    # at the specified bus and device /dev/spidev{bus}.{device}
    nrf_rx = RF24(SPI_BUS_RX, CSN_PIN_0, CE_PIN_0, SPI_BUS_NUM_0, SPI_DEV)
    nrf_tx = RF24(SPI_BUS_TX, CSN_PIN_1, CE_PIN_1, SPI_BUS_NUM_1, SPI_DEV)



    # set the Power Amplifier level to -12 dBm since this test example is
    # usually run with nRF24L01 transceivers in close proximity
    nrf_rx.pa_level = POWER_LEVEL
    nrf_tx.pa_level = POWER_LEVEL

    # set the number of connection retries and the the delay between each try
    nrf_rx.set_auto_retries(DELAY, COUNT)
    nrf_tx.set_auto_retries(DELAY, COUNT)

    # set the data_rate
    nrf_rx.data_rate = DATA_RATE
    nrf_tx.data_rate = DATA_RATE

    # enable the Dynamic Payloads
    nrf_rx.crc = CRC_LENGTH
    nrf_tx.crc = CRC_LENGTH

    #nrf_rx.print_details()
    #nrf_tx.print_details()

    # addresses needs to be in a buffer protocol object (bytearray)
    address = [b"Base", b"Node"]

    nrf_tx.open_tx_pipe(address[role])
    nrf_rx.open_rx_pipe(1, address[not role])

    nrf_tx.flush_tx()
    nrf_rx.flush_rx()

    return (nrf_rx, nrf_tx)

def fragment(data: bytes) -> list:
    """ Fragments incoming binary data in bytes

    Args:
        data (bytes): Binary data converted with "bytes"

    Returns:
        list: list of fragments 
    """

    fragments = []
    dataLength = len(data)

    if (dataLength == 0):
        return

    id = 1

    while data:
        if (len(data) <= 30):
            id = 65535

        fragments.append(id.to_bytes(2, 'big') + data[:FRAG_SIZE])
        data = data[FRAG_SIZE:]
        id += 1

    return fragments

def tx(nrf_tx: RF24, packet: bytes):
    """ Transmit packet to the active writing pipe. Fragments bytes if needed.

    Args:
        packet (bytes): bytes to be transmitted

    """
    nrf_tx.stopListening()
    fragments = fragment(packet)

    for frag in fragments:
        result = nrf_tx.write(frag)
        if (result):
            print("Frag sent id: ", frag[:2])
        else:
            print("Frag not sent: ", frag[:2])

def radio_tx(nrf_tx: RF24):
    while True:
        with cond_in:
            while not len(tun_in_queue) > 0:
                cond_in.wait()
            packet = tun_in_queue.pop()
        tx(nrf_tx, packet)

def tun_rx():
    """ Waits for new packets from tun device
    and forwards the packet to radio writing pipe
    """
    while True:
        buffer = tun.read()
        if len(buffer):
            print("Got package from tun interface:\n\t", buffer, "\n")
            tx(buffer)

def radio_rx(nrf_rx:RF24):
    """ Waits for incoming packet on reading pipe 
    and forwards the packet to tun interface
    """
    nrf_rx.listen = True
    buffer = []
    while True:
        has_payload = nrf_rx.available()
        if has_payload:
            pSize = nrf_rx.get_payload_length()
            fragment = nrf_rx.read(pSize)
            id = int.from_bytes(fragment[:2], 'big')
            #print("Frag received with id: ", id)

            buffer.append(fragment[2:])

            if id == 0xFFFF:  # packet is fragmented and this is the first fragment
                packet = b''.join(buffer)
                #print("Packet received:\n\t", packet, "\n")
                buffer.clear()

                with cond_out:
                    tun_out_queue.append(packet)
                    cond_out.notify()

def tun_tx():

    while True:
        with cond_out:
            while not len(tun_out_queue) > 0:
                cond_out.wait()
            packet = tun_out_queue.pop()

        tun.write(packet)

def main():
    rx_radio, tx_radio = setup(1)
    radio_rx_thread = threading.Thread(target=radio_rx(rx_radio), args=())
    radio_tx_thread = threading.Thread(target=radio_tx(tx_radio), args=())
    tun_rx_thread = threading.Thread(target=tun_rx, args=())
    tun_tx_thread = threading.Thread(target=tun_tx, args=())
    radio_rx_thread.start()
    radio_tx_thread.start()
    time.sleep(0.05)
    tun_rx_thread.start()
    tun_tx_thread.start()
    
    radio_rx_thread.join()
    radio_tx_thread.join()
    tun_rx_thread.join()
    tun_tx_thread.join()
    #rx_radio.print_details()
    #tx_radio.print_details()

if __name__ == "__main__":
    main()
