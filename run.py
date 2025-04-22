import subprocess
import sys
import time
import threading
import webbrowser
import os

def run_server():
    """Run the FastAPI server"""
    print("Starting MCP Server...")
    if os.name == 'nt':  # Windows
        process = subprocess.Popen([sys.executable, "-m", "app.main"], 
                                  creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:  # Unix/Linux/Mac
        process = subprocess.Popen([sys.executable, "-m", "app.main"])
    return process

def run_ui():
    """Run the Gradio UI"""
    print("Starting Gradio UI...")
    if os.name == 'nt':  # Windows
        process = subprocess.Popen([sys.executable, "-m", "app.ui.gradio_app"], 
                                  creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:  # Unix/Linux/Mac
        process = subprocess.Popen([sys.executable, "-m", "app.ui.gradio_app"])
    return process

def open_browser():
    """Open web browser to UI after a delay"""
    time.sleep(5)  # Wait for servers to start
    print("Opening browser...")
    webbrowser.open("http://localhost:7860")

if __name__ == "__main__":
    # Check if Python environment has required packages
    try:
        import uvicorn
        import fastapi
        import gradio
    except ImportError:
        print("Missing required packages. Please install dependencies:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    
    # Start server and UI processes
    server_process = run_server()
    time.sleep(2)  # Wait for server to start
    ui_process = run_ui()
    
    # Open browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    print("Application running!")
    print("FastAPI server: http://localhost:8000")
    print("Gradio UI: http://localhost:7860")
    print("Press Ctrl+C to stop all processes...")
    
    try:
        # Keep the script running
        server_process.wait()
    except KeyboardInterrupt:
        print("Stopping application...")
        server_process.terminate()
        ui_process.terminate()
        print("Application stopped.") 