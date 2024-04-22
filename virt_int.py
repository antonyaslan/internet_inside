"""

virt_int.py

Methods for creating, writing to, reading from and destroying TUN interfaces for use in PyG

"""

from pytun import TunTapDevice 

IFACE = 'PyG'

def create_tun(name=IFACE) -> TunTapDevice:
    tun = TunTapDevice(name)
    tun.addr = '10.1.1.1'
    tun.dstaddr = '10.1.1.2'
    tun.netmask = '255.255.255.0'
    tun.up()
    return tun

def destroy_tun(tun: TunTapDevice):
    tun.close()

def read_tun(tun: TunTapDevice, size):
    buf = tun.read(size)
    return buf

def write_tun(tun: TunTapDevice, buf):
    tun.write(buf)
