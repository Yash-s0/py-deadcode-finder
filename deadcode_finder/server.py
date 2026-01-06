"""
Simple HTTP server for handling dead code removal requests.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import threading
from pathlib import Path
from deadcode_finder.remover import CodeRemover


class RemovalHandler(BaseHTTPRequestHandler):
    """HTTP request handler for code removal operations."""
    
    remover = None
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests for code removal."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            action = data.get('action')
            response = {'status': 'error', 'message': 'Unknown action'}
            
            if action == 'remove_import':
                response = self.remover.remove_import(
                    data['file'],
                    data['name'],
                    data['line']
                )
            elif action == 'remove_function':
                response = self.remover.remove_function(
                    data['file'],
                    data['name'],
                    data['line']
                )
            elif action == 'remove_class':
                response = self.remover.remove_class(
                    data['file'],
                    data['name'],
                    data['line']
                )
            elif action == 'restore':
                response = self.remover.restore_from_backup(data['backup'])
            elif action == 'get_changes':
                response = {
                    'status': 'success',
                    'changes': self.remover.get_changes_log()
                }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
        
        except Exception as e:
            error_response = {'status': 'error', 'message': str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class RemovalServer:
    """Manages the HTTP server for code removal."""
    
    def __init__(self, root_path: str, port: int = 8765):
        self.root_path = root_path
        self.port = port
        self.server = None
        self.thread = None
        RemovalHandler.remover = CodeRemover(root_path)
    
    def start(self):
        """Start the server in a background thread."""
        if self.server is None:
            self.server = HTTPServer(('localhost', self.port), RemovalHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return f"http://localhost:{self.port}"
        return None
    
    def stop(self):
        """Stop the server."""
        if self.server:
            self.server.shutdown()
            self.server = None
            self.thread = None
    
    def is_running(self):
        """Check if server is running."""
        return self.server is not None
