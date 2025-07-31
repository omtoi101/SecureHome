import json, threading, os, sys, signal, subprocess, time
from dependencies.Runner import Runner

cd = os.path.dirname(__file__)
with open(os.path.join(cd, "config.json"), "r") as conf_file:
    config = json.load(conf_file)

webserver = config["settings"]["webserver"]
bot = config["settings"]["discord_bot"]
debug = config["settings"]["debug"]

runner = Runner(cd, debug)

# Global process references
processes = {
    'webserver': None,
    'bot': None,
    'security': None
}

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nShutting down SecureHome...')
    stop_all_processes()
    sys.exit(0)

def stop_all_processes():
    """Stop all running processes"""
    for name, process in processes.items():
        if process and process.poll() is None:
            print(f"Stopping {name}...")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                print(f"Error stopping {name}: {e}")

def start_webserver():
    """Start the webserver process"""
    if not processes['webserver'] or processes['webserver'].poll() is not None:
        processes['webserver'] = subprocess.Popen([
            'python', os.path.join(cd, 'server.py')
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        print("Webserver started")
        return True
    return False

def start_bot():
    """Start the Discord bot process"""
    if not processes['bot'] or processes['bot'].poll() is not None:
        processes['bot'] = subprocess.Popen([
            'python', os.path.join(cd, 'bot.py')
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        print("Discord bot started")
        return True
    return False

def start_security():
    """Start the security system process"""
    if not processes['security'] or processes['security'].poll() is not None:
        processes['security'] = subprocess.Popen([
            'python', os.path.join(cd, 'main.py')
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        print("Security system started")
        return True
    return False

def stop_process(name):
    """Stop a specific process"""
    if processes[name] and processes[name].poll() is None:
        try:
            processes[name].terminate()
            processes[name].wait(timeout=5)
            print(f"{name.capitalize()} stopped")
            return True
        except subprocess.TimeoutExpired:
            processes[name].kill()
            print(f"{name.capitalize()} force killed")
            return True
        except Exception as e:
            print(f"Error stopping {name}: {e}")
            return False
    return True

def restart_process(name):
    """Restart a specific process"""
    print(f"Restarting {name}...")
    stop_process(name)
    time.sleep(2)
    
    if name == 'webserver':
        return start_webserver()
    elif name == 'bot':
        return start_bot()
    elif name == 'security':
        return start_security()
    return False

def main_loop():
    """Main control loop"""
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("SecureHome Control System")
    print("Starting services...")
    
    # Start services based on config
    if webserver:
        start_webserver()
    
    if bot:
        start_bot()
    
    # Always start security system
    #start_security()
    
    print("\nSecureHome is running. Press Ctrl+C to stop all services.")
    print("Services can also be controlled via the web interface.")
    
    try:
        # Monitor processes
        while True:
            time.sleep(5)
            
            # Check if processes are still running
            for name, process in processes.items():
                if process and process.poll() is not None:
                    print(f"Warning: {name} process has stopped unexpectedly")
                    
            # You could add automatic restart logic here if needed
            
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    # Check for command line arguments for individual service control
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "webserver":
            runner.exec([f'python "{cd}\\server.py"'], "web")
        elif command == "bot":
            runner.exec([f'python "{cd}\\bot.py"'], "bot")
        elif command == "security":
            runner.exec([f'python "{cd}\\main.py"'], "sec")
        elif command == "stop":
            stop_all_processes()
        else:
            print("Usage: python run.py [webserver|bot|security|stop]")
    else:
        # Run the main control loop
        main_loop()