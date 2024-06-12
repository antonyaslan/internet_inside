from pyg_control_system import WaterTank, get_water_height, update_process
from threading import Lock

class Process(object):
    def __init__(self):
        self.process_lock = Lock()
        self.process = WaterTank()
        self.water_height = 0.0

    def update_water_height(self, control_signal: float):
        with self.process_lock:
            update_process(self.process, control_signal)
            self.water_height = get_water_height(self.process)
    
    def get_water_height(self) -> float:
        current_water_height = 0.0
        with self.process_lock:
            current_water_height = self.water_height
        return current_water_height
