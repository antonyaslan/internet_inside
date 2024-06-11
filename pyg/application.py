from typing import Tuple
import board
import queue
from digitalio import DigitalInOut
from rf24 import RF24
import spidev
import subprocess
import threading
import time
from tun_interface import Tun
import logging
from process import Process

cond_in = threading.Condition()
tun_in_queue = queue.Queue()

cond_out = threading.Condition()
tun_out_queue = queue.Queue()

do_run = threading.Event()

process = Process()
control_signal = 0.0
control_signal_lock = threading.Lock()

""" Process parameters """
SET_POINT = 0.02
PROCESS_UPDATE_PERIOD = 1
PROCESS_SAMPLE_PERIOD = 5

""" Invalid default values for scoping """
SPI_BUS, CSN_PIN, CE_PIN = (None, None, None)

""" Constants for CE & CSN pins for the two SPI buses """

CE_BUS_0 = board.D22
CE_BUS_1 = board.D24
CSN_BUS_0 = 0
CSN_BUS_1 = 10

""" We only use device 0 for the two SPI buses """

SPI_DEV = 0

""" Radio Parameters """

POWER_LEVEL = -12 #DBM
DELAY = 500 #us
COUNT = 10 
DATA_RATE = 2 #MBps
CRC_LENGTH = 2 #Bytes

""" Fragments size """
FRAG_SIZE = 30

LAST_PACKET_ID = 0xFFFF

TUN_IF_NAME = "LongG"

MOBILE_IP = "125.100.1.2"
BASE_IP = "125.100.1.1"
TUN_IF_MASK = "255.255.255.0"

CONTROL_SERVER_IP = "192.168.12.46"
CONTROL_SERVER_PORT = "8080"

""" Define tun device """
tun = Tun(if_name=TUN_IF_NAME)

""" Setup the two radios """
def setup(role) -> Tuple[RF24, RF24]:
    
    tun.create()

    if role == 1:
        """ Mobile """
        tun.setup_if(ip=MOBILE_IP, mask=TUN_IF_MASK)

        command = 'ip route add 8.8.8.8 via '+BASE_IP+' dev '+TUN_IF_NAME
        subprocess.run(command, shell=True)
        subprocess.run('ip route add ' + CONTROL_SERVER_IP + ' via ' + BASE_IP + ' dev ' + TUN_IF_NAME, shell=True)


    if role == 0:
        """ Base """
        tun.setup_if(ip=BASE_IP, mask=TUN_IF_MASK)
        subprocess.run('iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE', shell=True)
        command = 'sudo iptables -A FORWARD -i eth0 -o '+TUN_IF_NAME+' -m state --state RELATED,ESTABLISHED -j ACCEPT'
        subprocess.run(command,shell=True)
        subprocess.run('sudo iptables -A FORWARD -i '+TUN_IF_NAME+' -o eth0 -j ACCEPT', shell=True)


    """ Create SPI bus object """
    SPI_BUS_RX = spidev.SpiDev()
    SPI_BUS_TX = spidev.SpiDev()

    """ Radio 0 """
    CE_PIN_0 = DigitalInOut(board.D22)
    CSN_PIN_0 = CSN_BUS_0
    SPI_BUS_NUM_0 = 0
    """ Radio 1 """
    CE_PIN_1 = DigitalInOut(board.D24)
    CSN_PIN_1 = CSN_BUS_1 
    SPI_BUS_NUM_1 = 1

    """ 
        Initialize the nRF24L01 on the spi bus object with the specified CE & CSN pin:
        At the specified bus and device /dev/spidev{bus}.{device}
    """
    nrf_rx = RF24(SPI_BUS_RX, CSN_PIN_0, CE_PIN_0, SPI_BUS_NUM_0, SPI_DEV)
    nrf_tx = RF24(SPI_BUS_TX, CSN_PIN_1, CE_PIN_1, SPI_BUS_NUM_1, SPI_DEV)



    """ 
        Set the Power Amplifier level to -12 dBm.
        
        Usually run with nRF24L01 transceivers in close proximity 
    """
    nrf_rx.pa_level = POWER_LEVEL
    nrf_tx.pa_level = POWER_LEVEL

    """ Set the number of connection retries and the the delay between each try """
    """ Setting these configs makes it not work, could be worth looking into changing DELAY and COUNT? TODO"""
    nrf_rx.set_auto_retries(DELAY, COUNT)
    nrf_tx.set_auto_retries(DELAY, COUNT)

    """ Set the data_rate """
    nrf_rx.data_rate = DATA_RATE
    nrf_tx.data_rate = DATA_RATE

    nrf_rx.crc = CRC_LENGTH
    nrf_tx.crc = CRC_LENGTH


    """ Αddresses needs to be in a buffer protocol object (bytearray)"""
    address = [b"1Base", b"2Node"]

    nrf_tx.open_tx_pipe(address[role])
    nrf_tx.open_rx_pipe(1, address[not role])
    nrf_rx.open_tx_pipe(address[role])
    nrf_rx.open_rx_pipe(1, address[not role])

    nrf_tx.flush_tx()
    nrf_rx.flush_rx()

    #nrf_rx.print_details()
    #nrf_tx.print_details()

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
        if (len(data) <= FRAG_SIZE):
            id = LAST_PACKET_ID

        fragments.append(id.to_bytes(2, 'big') + data[:FRAG_SIZE])
        data = data[FRAG_SIZE:]
        id += 1

    return fragments

def tx(nrf_tx: RF24, packet: bytes):
    """ Transmit packet to the active writing pipe. Fragments bytes if needed.

    Args:
        packet (bytes): bytes to be transmitted

    """
    nrf_tx.listen = False
    fragments = fragment(packet)

    for frag in fragments:
        # result = nrf_tx.write(frag)
        result = nrf_tx.send(frag)
        if (result):
            print("Tx Radio --> Frag sent id: ", frag[:2])
        else:
            print("Tx Radio --> Frag not sent: ", frag[:2])

def radio_tx(nrf_tx: RF24):
    while do_run.is_set():
        #with cond_in:
            #while not len(tun_in_queue) > 0:
                #cond_in.wait()
        try:
            packet = tun_in_queue.get(timeout=3)
            tx(nrf_tx, packet)
            print("Radio TX --> Transmitting a package:\n\t", packet, "\n")
        except queue.Empty:
            print("Radio Tx --> No packets found in queue")

    print("Radio TX thread is shutting down")

def tun_rx():
    """ Waits for new packets from tun device
    and forwards the packet to radio writing pipe
    """
    logging.debug("[TUN RX] Thread starting")
    while do_run.is_set():
        logging.debug("[TUN RX] (Re)starting loop")
        logging.debug("[TUN RX] Attempting to read from TUN interface")
        (buffer, success) = tun.read(blocking=True,timeout=3)
        logging.debug("[TUN RX] Attempt done")
        if success:
            tun_in_queue.put(buffer)
            print("Rx Tun --> Got package from tun interface:\n\t", buffer, "\n")
            logging.debug("[TUN RX] Got package from tun interface: {}".format(buffer))
        else:
            print("Rx Tun --> Could not read from tun interface")
            logging.debug("[TUN RX] Could not read from tun interface")
        #if len(buffer):
        #    print("Got package from tun interface:\n\t", buffer, "\n")
        #    tx(buffer)
    print("TUN RX thread is shutting down")

def radio_rx(nrf_rx:RF24):
    """ Waits for incoming packet on reading pipe 
    and forwards the packet to tun interface
    """
    nrf_rx.listen = True

    buffer = []
    while do_run.is_set():
        # has_payload = nrf_rx.available()
        if nrf_rx.available():
            # packet_size = nrf_rx.get_payload_length(nrf_rx.pipe)
            payload_size, pipe_number = (nrf_rx.any(), nrf_rx.pipe)
            fragment = nrf_rx.read(payload_size)
            id = int.from_bytes(fragment[:2], 'big')
            print("Rx Radio --> Frag received with id: {}, size: {}, pipe number: {}".format(id, payload_size, pipe_number))

            buffer.append(fragment[2:])

            if id == LAST_PACKET_ID:  # packet is fragmented and this is the first fragment
                packet = b''.join(buffer)
                print("Rx Radio --> Packet received:\n\t", packet, "\n")
                buffer.clear()
                tun_out_queue.put(packet)
                #with cond_out:
                #    tun_out_queue.append(packet)
                #    cond_out.notify()
    print("Radio RX thread is shutting down")
    
def tun_tx():

    while do_run.is_set():
        print("[TUN TX] Loop")
        #with cond_out:
        #    while not len(tun_out_queue) > 0:
        #        cond_out.wait()
        try:
            packet = tun_out_queue.get(timeout=3)
            print("[TUN TX] Got through tun out queue")
            (num_bytes, success) = tun.write(packet, blocking=True,timeout=3)
            print("[TUN TX] Got through tun write")
            if success:
                print("[TUN TX] Wrote a packet to tun interface:\n\t", packet, "\n")
            else:
                print("[TUN TX] Could not write a packet to tun interface")
        except queue.Empty:
            print("[TUN TX] No packets found in queue")
    print("TUN TX thread is shutting down")

def process():
    logging.debug("Water tank process thread starting")
    while do_run.is_set():
        start_time = time.monotonic_ns()
        process.update_water_height()
        logging.debug("Water tank process updated")
        end_time = time.monotonic_ns()

def main():
    logging.basicConfig(filename='tun_rx.log', level=logging.DEBUG) 
    node = int(input("Select node role. 0:Base 1:Mobile :"))
    rx_radio, tx_radio = setup(node)
    radio_rx_thread = threading.Thread(target=radio_rx, args=(rx_radio,))
    radio_tx_thread = threading.Thread(target=radio_tx, args=(tx_radio,))
    tun_rx_thread = threading.Thread(target=tun_rx, args=())
    tun_tx_thread = threading.Thread(target=tun_tx, args=())
    do_run.set()
    radio_rx_thread.start()
    radio_tx_thread.start()
    time.sleep(0.05)
    tun_rx_thread.start()
    tun_tx_thread.start()

    while True:
        try:
            time.sleep(0.01)
        except KeyboardInterrupt:
            # Clear run condition, making all threads shut down
            do_run.clear()

            # Join all threads
            radio_rx_thread.join()
            radio_tx_thread.join()
            tun_rx_thread.join()
            tun_tx_thread.join()

            print("[MAIN] All other threads closed, removing NAT interface and IP table/IP route rules")

            # Base
            if node == 0:
                # Remove iptable forwarding rules
                subprocess.run('sudo iptables -D FORWARD -i eth0 -o LongG -m state --state RELATED,ESTABLISHED -j ACCEPT', shell=True)
                subprocess.run('sudo iptables -D FORWARD -i LongG -o eth0 -j ACCEPT', shell=True)
                # Remove iptable NAT table rules
                subprocess.run('sudo iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE', shell=True)
            # Mobile
            else:
                subprocess.run('sudo ip route del 8.8.8.8 via 125.100.1.1 dev LongG', shell=True)

            # Close TUN interface
            tun.close()
            print("Main thread shutting down")

            break

if __name__ == "__main__":
    main()
