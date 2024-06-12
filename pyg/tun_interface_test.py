from tun_interface import Tun

def main():
    iface = Tun("testif")
    iface.create()
    iface.setup_if("125.90.1.1", "255.255.255.0")

    buffer = iface.read(blocking=True, timeout=3)
    print(buffer)
    buffer = iface.read(blocking=True, timeout=3)
    print(buffer)
    buffer = iface.read(blocking=True, timeout=3)
    print(buffer)

    write_result = iface.write(buffer, blocking=True, timeout=3)
    print(write_result)

    while True:
        print("Press `q` to exit")
        choice = input("Option: ")
        if (choice == "q"):
            iface.close()
            break


if __name__ == '__main__':
    main()