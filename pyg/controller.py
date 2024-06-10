from pyg_control_system import PID, control_it, get_control_signal
from threading import Lock

class Controller(object):
    def __init__(self):
        self.controller = PID()
        self.control_signal = 0.0
        self.control_lock = Lock()

    def control(self, measured_value, set_point):
        with self.control_lock:
            control_it(self.controller, set_point, measured_value)
        
    def get_control_signal(self):
        current_control_signal = 0.0
        with self.control_lock:
            current_control_signal = get_control_signal(self.controller)
        return current_control_signal