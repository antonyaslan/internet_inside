import struct
from fcntl import ioctl
import threading
import math
import subprocess
import os
from typing import Tuple

class Tun(object):
    def __init__(self, if_name):
        self.read_lock = threading.RLock()
        self.write_lock = threading.RLock()
        self.if_name = if_name
        self.handle = None
        self.ip = None
        self.mask = None
        self.gateway = None
        self.n_mask_bits = 0

    def create(self):
        """
        Creates the TUN interface device in the file system using the name provided
        when creating the class instance.
        The TUN device is able to be accessed by all users and groups, and does
        not persist.
        """
        LINUX_IFF_TUN = 0x0001
        LINUX_IFF_NO_PI = 0x1000
        LINUX_TUNSETIFF = 0x400454CA
        TUNSETOWNER = 0x400454cc
        TUNSETGROUP = 0x400454ce
        TUNSETPERSIST = 0x400454cb
        O_RDWR = 0x2
        tun = os.open("/dev/net/tun", O_RDWR)
        flags = LINUX_IFF_TUN | LINUX_IFF_NO_PI
        if_name_b = self.if_name.encode() + b'\x00'*(16-len(self.if_name.encode()))
        ifs = struct.pack("16sH22s", if_name_b, flags, b'\x00'*22)
        ioctl(tun, LINUX_TUNSETIFF, ifs)
        ioctl(tun, TUNSETOWNER, struct.pack("H", 1000))
        ioctl(tun, TUNSETGROUP, struct.pack("H", 1000))
        # Don't persist
        ioctl(tun, TUNSETPERSIST, struct.pack("B", False))

        self.handle = tun
    
    def _calc_mask_bits(self, mask: str):
        # Calculate the number of mask bits based on the mask provided
        # E.g.: with a mask of 255.255.255.0, we have 24 mask bits
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
        """
        Sets up the TUN interface that was created with `create()`. Uses the provided
        ip and mask, as well as an optional gateway (default gateway 0.0.0.0)
        """
        self.ip = ip
        self.mask = mask
        self.gateway = gateway
        n_mask_bits = self._calc_mask_bits(mask)
        self.n_mask_bits = n_mask_bits

        subprocess.run("ip addr add "+ip+"/%d"%n_mask_bits+" dev " + self.if_name, shell=True)
        subprocess.run("ip link set dev "+self.if_name+" up", shell=True)

    def close(self):
        """
        Close and destroy this TUN interface.
        """
        os.close(self.handle)
        subprocess.run("ip addr del "+self.ip+"/%d"%self.n_mask_bits+ " dev " + self.if_name, shell=True)
        subprocess.run("ip tuntap del mode tun " + self.if_name, shell=True)

    def read(self, blocking=False, timeout=-1, size=1522) -> Tuple[bytes, bool]:
        """
        Read from this TUN interface. Can be made blocking with a timeout, to
        block until the read lock is acquired. Otherwise if the lock is taken by
        another thread, return immediatly without performing any reading.
        """
        data = None 
        success = self.read_lock.acquire(blocking=blocking, timeout=timeout)
        if success:
            data = os.read(self.handle, size)
            self.read_lock.release()
        return (data, success)

    def write(self, data, blocking=False, timeout=-1) -> Tuple[int, bool]:
        """
        Write to this TUN interface. Can be made blocking with a timeout, to
        block until the write lock is acquired. Otherwise if the lock is taken by
        another thread, return immediatly without performing any writing.
        """
        num_bytes = 0
        success = self.write_lock.acquire(blocking=blocking, timeout=timeout)
        if success:
            num_bytes = os.write(self.handle, data)
            self.write_lock.release()
        return (num_bytes, success)