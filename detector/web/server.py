"""Web server for dashboard."""

import webbrowser
from threading import Timer

from detector.web.api import create_app


def open_browser(url):
    """Open browser after a delay."""
    webbrowser.open(url)


def run_server(host="127.0.0.1", port=5000, debug=False, open_browser_flag=True):
    """Start the Flask development server."""
    app = create_app()

    url = "http://{}:{}".format(host, port)
    print("\n🚀 Starting gh-api-graveyard dashboard...")
    print("📊 Dashboard: {}".format(url))
    print("🔌 API: {}/api".format(url))
    print("\nPress Ctrl+C to stop\n")

    if open_browser_flag and host in ["127.0.0.1", "localhost"]:
        # Open browser after 1 second delay
        Timer(1.0, open_browser, args=[url]).start()

    app.run(host=host, port=port, debug=debug)
