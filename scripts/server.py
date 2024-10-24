# This file is only to be used for testing. It will serve a
# csv file that can be fetched by map_data_processor.py
# that has less records, so we don't burn through API quotas

from http.server import HTTPServer, SimpleHTTPRequestHandler
import os


class CSVHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Set CSV content type
        if self.path.endswith(".csv"):
            self.send_response(200)
            self.send_header("Content-type", "text/csv")
            self.end_headers()

            # Read and serve the CSV file
            with open(os.path.join(os.getcwd(), self.path.lstrip("/")), "rb") as f:
                self.wfile.write(f.read())
        else:
            super().do_GET()


def run_server(port=8081):
    server_address = ("", port)
    httpd = HTTPServer(server_address, CSVHandler)
    print(f"Server running at http://localhost:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
