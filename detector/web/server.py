"""Web server for dashboard."""

import socket
import webbrowser
from threading import Timer

from detector.web.api import create_app


def open_browser(url):
    """Open browser after a delay."""
    webbrowser.open(url)


def find_available_port(host, start_port, max_attempts=10):
    """
    Find an available port starting from start_port.
    
    Args:
        host: Host to bind to
        start_port: Port to start searching from
        max_attempts: Maximum number of ports to try
    
    Returns:
        Available port number
    """
    # First try the requested port range
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            sock.close()
            return port
        except OSError:
            # Port is in use, try next one
            continue
    
    # If all preferred ports are taken, let OS choose any available port
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, 0))  # Port 0 means: let OS choose
        port = sock.getsockname()[1]
        sock.close()
        return port
    except OSError:
        # This should never happen, but just in case
        return None


def run_server(host="127.0.0.1", port=5000, debug=False, open_browser_flag=True):
    """Start the Flask development server."""
    app = create_app()

    # Find available port
    original_port = port
    available_port = find_available_port(host, port)
    
    if available_port is None:
        print(f"❌ Could not find any available port")
        print(f"   This should never happen - please check your system")
        return
    
    if available_port != original_port:
        if available_port < original_port + 10:
            # Port in preferred range
            print(f"ℹ️  Port {original_port} is in use, using port {available_port} instead")
        else:
            # OS-assigned port
            print(f"ℹ️  Ports {original_port}-{original_port + 9} are in use")
            print(f"   Using OS-assigned port {available_port}")
    
    url = "http://{}:{}".format(host, available_port)
    print("\n🚀 Starting gh-api-graveyard dashboard...")
    print("📊 Dashboard: {}".format(url))
    print("🔌 API: {}/api".format(url))
    print("\nPress Ctrl+C to stop\n")

    if open_browser_flag and host in ["127.0.0.1", "localhost"]:
        # Open browser after 1 second delay
        Timer(1.0, open_browser, args=[url]).start()

    app.run(host=host, port=available_port, debug=debug)
