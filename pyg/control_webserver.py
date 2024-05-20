import http.server
import socketserver
import logging
from urllib.parse import urlparse, parse_qs
from pyg_control_system import PID, control_it, get_control_signal
import sys

PORT = 8080

class RequestHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, pid: PID, set_point):
        super.__init__
        self.pid = pid
        self.set_point = set_point

    def do_GET(self) -> None:
        # Parse measured value from URL
        parsed_path = urlparse(self.path)
        value_str = parsed_path.path.lstrip("/")
        if value_str.replace('.', '', 1).isdigit():
            measured_value = float(value_str)
        else:
            self.send_error(400, "Bad request: measured value must be a floating-point type value")

        control_it(self.pid, self.set_point, measured_value)        

        control_signal = get_control_signal(self.pid)

        self.send_response(200)
        self.send_header('Content-type', 'application/octet-stream')
        self.send_header('Content-Length', sys.getsizeof(control_signal))
        self.end_headers()
        self.wfile.write(control_signal)

        client_ip = self.client_address[0]
        log_message = (f"Request: {self.path} | "
                       f"Measured value: {measured_value}"
                       f"Payload: {control_signal} | "
                       f"By: {client_ip}")

        logging.info(log_message)
        
def run(server_class=http.server.HTTPServer):
    logging.basicConfig(filename='control_server.log', level=logging.INFO) 
    server_address = ('', PORT)
    pid = PID()
    set_point = 0.02
    handler_class = RequestHandler(pid, set_point)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {PORT}")
    logging.info(f"Starting server on port {PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()