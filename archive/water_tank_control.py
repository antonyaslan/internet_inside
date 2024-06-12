from pyg_control_system import PID, control_it, get_control_signal
from pyg_control_system import WaterTank, update_process, get_water_height, get_water_volume
from threading import Lock, Event, Thread
import time
import matplotlib.pyplot as plt

PROCESS_PERIOD = 1
SAMPLING_PERIOD = 5
STATUS_PERIOD = 2
SET_POINT = 0.02

process_lock = Lock()
control_signal_lock = Lock()

def process(water_tank: WaterTank, pid: PID, run_loop: Event):
    print("[PROCESS] Water tank process thread starting")

    u = 0.0

    while run_loop.is_set():
        print("[PROCESS] Water tank process updating")

        start_timer = time.monotonic_ns()
        control_signal_lock.acquire()
        process_lock.acquire()
        u = get_control_signal(pid)
        update_process(water_tank, u)
        process_lock.release()
        control_signal_lock.release()

        print("[PROCESS] Water tank process updated")

        end_timer = time.monotonic_ns()

        time.sleep(PROCESS_PERIOD - ((end_timer-start_timer)/10e9))
    
    print("[PROCESS] Process thread shutting down")

def controller(pid: PID, water_tank: WaterTank, run_loop: Event):
    print("[CONTROLLER] PID controller thread starting")

    h = 0.0

    while run_loop.is_set():
        print("[CONTROLLER] PID controller updating")

        start_timer = time.monotonic_ns()

        process_lock.acquire()
        control_signal_lock.acquire()
        h = get_water_height(water_tank)
        control_it(pid, SET_POINT, h)
        control_signal_lock.release()
        process_lock.release()

        print("[CONTROLLER] PID controller updated")

        end_timer = time.monotonic_ns()

        time.sleep(SAMPLING_PERIOD - ((end_timer-start_timer)/10e9))

    print("[CONTROLLER] PID controller thread shutting down")

def status(pid: PID, water_tank: WaterTank, run_loop: Event):

    print("[STATUS] Status thread starting")

    u = 0.0
    h = 0.0
    v = 0.0

    measured_values = []

    while run_loop.is_set():

        start_timer = time.monotonic_ns()

        process_lock.acquire()
        control_signal_lock.acquire()
        h = get_water_height(water_tank)
        u = get_control_signal(pid)
        v = get_water_volume(water_tank)
        control_signal_lock.release()
        process_lock.release()

        print("[STATUS] Current water height: {}, current water volume: {}, current flow rate: {}".format(h, v, u))

        measured_values.append(h)
        end_timer = time.monotonic_ns()

        time.sleep(STATUS_PERIOD - ((end_timer-start_timer)/10e9))

    fig, ax = plt.subplots()
    ax.plot(measured_values)
    fig.savefig("measured_values.png")
    

    print("[STATUS] Status thread shutting down")




def main():
    run_loop = Event()
    run_loop.set()

    pid = PID()
    water_tank = WaterTank()

    pid_thread = Thread(target=controller, args=(pid, water_tank, run_loop,))
    process_thread = Thread(target=process, args=(water_tank, pid, run_loop,))
    status_thread = Thread(target=status, args=(pid, water_tank, run_loop,))

    pid_thread.start()
    process_thread.start()
    status_thread.start()

    while True:
        try:
            time.sleep(0.01)
        except KeyboardInterrupt:
            run_loop.clear()
            print("[MAIN] Shutting down...")
            time.sleep(5)
            break

if __name__ == '__main__':
    main()