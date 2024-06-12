"""
PyG

Implementation of IP stack on Raspberry Pi5 with nRF24L01+ radios, implemented in python

Drivers based on https://github.com/nRF24/CircuitPython_nRF24L01/, but adapted to this use case

"""
import time
import struct
import board
from digitalio import DigitalInOut
from threading import Thread
from rf24 import RF24
import spidev
from archive.virt_int import create_tun, destroy_tun, read_tun, write_tun

# invalid default values for scoping
SPI_BUS, CSN_PIN, CE_PIN = (None, None, None)

# Constants for CE & CSN pins for the two SPI buses
CE_BUS_0 = board.D22
CE_BUS_1 = board.D24
CSN_BUS_0 = 0
CSN_BUS_1 = 10

# We only use device 0 for the two SPI buses
SPI_DEV = 0


# Setup the two radios
def setup() -> (RF24, RF24):
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
    nrf_rx.pa_level = -12
    nrf_tx.pa_level = -12

    # addresses needs to be in a buffer protocol object (bytearray)
    address = [b"1Node", b"2Node"]

    # Make sure the radio number matches between the two different radio's RX and TX pipes!

    radio_number = 0

    # set TX address of RX node into the TX pipe
    nrf_tx.open_tx_pipe(address[radio_number])

    # set RX address of TX node into an RX pipe
    nrf_rx.open_rx_pipe(1, address[radio_number])

    return (nrf_rx, nrf_tx)

def tx(nrf_tx: RF24):
    payload = [0.0]
    """Transmits an incrementing integer every second"""
    nrf_tx.listen = False  # ensures the nRF24L01 is in TX mode

    count = 6

    while count:
        # use struct.pack to structure your data
        # into a usable payload
        buffer = struct.pack("<f", payload[0])
        # "<f" means a single little endian (4 byte) float value.
        start_timer = time.monotonic_ns()  # start timer
        result = nrf_tx.send(buffer)
        end_timer = time.monotonic_ns()  # end timer
        if not result:
            print("send() failed or timed out")
        else:
            print(
                "Transmission successful! Time to Transmit:",
                "{} us. Sent: {}".format((end_timer - start_timer) / 1000, payload[0]),
            )
            payload[0] += 0.01
        time.sleep(1)
        count -= 1

def rx(nrf_rx: RF24):
    payload = [0.0]
    """Polls the radio and prints the received value. This method expires
    after 6 seconds of no received transmission"""
    nrf_rx.listen = True  # put radio into RX mode and power up

    timeout = 6

    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        if nrf_rx.available():
            # grab information about the received payload
            payload_size, pipe_number = (nrf_rx.any(), nrf_rx.pipe)
            # fetch 1 payload from RX FIFO
            buffer = nrf_rx.read()  # also clears nrf.irq_dr status flag
            # expecting a little endian float, thus the format string "<f"
            # buffer[:4] truncates padded 0s if dynamic payloads are disabled
            payload[0] = struct.unpack("<f", buffer[:4])[0]
            # print details about the received packet
            print(
                "Received {} bytes on pipe {}: {}".format(
                    payload_size, pipe_number, payload[0]
                )
            )
            start = time.monotonic()

    # recommended behavior is to keep in TX mode while idle
    nrf_rx.listen = False  # put the nRF24L01 is in TX mode

def tun_test():
    tun = create_tun()

    buf = [0.0]
    done = False
    while not done:
        print("Select one of the following options:")
        print("1 - Read from TUN interface")
        print("2 - Write to TUN interface")
        print("3 - Close and destroy interface")
        choice = int(input("Pick an option: "))
        if choice == 1:
            buf = read_tun(tun, tun.mtu)
        elif choice == 2:
            write_tun(tun, buf)
        elif choice == 3:
            destroy_tun(tun)
            done = True
        else:
            print("Unknown choice")
            pass

def nrf_test():
    print("Simple test of two nRF24L01+ radios communicating with each other from the same chip")
    print("Setting up devices...")
    nrf_rx, nrf_tx = setup()
    print("Done!")
    print("Starting the two devices...")
    t_rx = Thread(target=rx, args=(nrf_rx,))
    t_tx = Thread(target=tx, args=(nrf_tx,))
    t_rx.start()
    t_tx.start()

    t_rx.join()
    t_tx.join()
    print("Simple test done.")

def main():
    print("What do you want to test? 1 = nRF24L01+ functionality, 2 = TUN")
    choice = int(input("Enter your choice: "))
    if choice == 1:
        nrf_test()
    elif choice == 2:
        tun_test()
    else:
        print("Unrecognized choice!")

if __name__ == "__main__":
    main()

