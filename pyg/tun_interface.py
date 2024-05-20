import struct
from fcntl import ioctl
import threading
import math
import subprocess
import os

class Tun(object):
    def __init__(self, if_name):
        self.read_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.if_name = if_name
        self.handle = None
        self.ip = None
        self.mask = None
        self.gateway = None
        self.n_mask_bits = 0

    def create(self):
        LINUX_IFF_TUN = 0x0001
        LINUX_IFF_NO_PI = 0x1000
        LINUX_TUNSETIFF = 0x400454CA
        TUNSETOWNER = 0x400454cc
        TUNSETGROUP = 0x400454ce
        TUNSETPERSIST = 0x400454cb
        tun = open("/dev/net/tun", "r+b", buffering=0)
        flags = LINUX_IFF_TUN | LINUX_IFF_NO_PI
        ifs = struct.pack("16sH22s", self.if_name, flags, b"")
        ioctl(tun, LINUX_TUNSETIFF, ifs)
        ioctl(tun, TUNSETOWNER, struct.pack("H", 1000))
        ioctl(tun, TUNSETGROUP, struct.pack("H", 1000))
        # Don't persist
        ioctl(tun, TUNSETPERSIST, struct.pack("B", False))

        self.handle = tun

        return self
    
    def _calc_mask_bits(self, mask: str):
        masks = mask.split('.')
        maskbits = 0
        if len(masks) == 4:
            for i in range(len(masks)):
                n_bit = math.log(256-int(masks[i]), 2)
                if n_bit == int(n_bit):
                    maskbits += 8-n_bit
                else:
                    return
        return int(maskbits)

    def setup_if(self, ip, mask, gateway="0.0.0.0"):
        self.ip = ip
        self.mask = mask
        self.gateway = gateway
        n_mask_bits = self._calc_mask_bits(mask)
        self.n_mask_bits = n_mask_bits

        subprocess.run("ip addr add "+ip+"/%d"%n_mask_bits+" dev " + self.if_name, shell=True)
        subprocess.run("ip link set dev "+self.if_name+" up", shell=True)

        return self

    def close(self):
        os.close(self.handle)
        subprocess.run("ip addr del "+self.ip+"/%d"%self.n_mask_bits+ " dev " + self.if_name, shell=True)
        subprocess.run("ip tuntap del mode tun " + self.if_name, shell=True)

    def read(self, blocking=False, timeout=-1, size=1522):
        self.read_lock.acquire(blocking=blocking, timeout=timeout)
        data = os.read(self.handle, size)
        self.read_lock.release()
        return data

    def write(self, data, blocking=False, timeout=-1):
        result = 0
        self.write_lock.acquire(blocking=blocking, timeout=timeout)
        result = os.write(self.handle, data)
        self.write_lock.release()
        return result