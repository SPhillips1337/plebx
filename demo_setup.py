#!/usr/bin/env python3
"""
Demo script showing Plebbit daemon setup and P2P bridge usage
"""
import subprocess
import sys
import time
import asyncio
import os

def install_bitsocial_cli():
    """Install Bitsocial CLI if not available"""
    try:
        result = subprocess.run(['npm', 'list', '-g', 'bitsocial-cli'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Bitsocial CLI already installed")
            return True
    except FileNotFoundError:
        print("❌ npm not found. Please install Node.js from https://nodejs.org/")
        return False
    
    print("📦 Installing Bitsocial CLI...")
    install_cmd = ['npm', 'install', '-g', 'bitsocialhq/bitsocial-cli']
    result = subprocess.run(install_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Bitsocial CLI installed successfully")
        return True
    else:
        print(f"❌ Failed to install Bitsocial CLI: {result.stderr}")
        return False

def start_plebbit_daemon():
    """Start Plebbit daemon in background"""
    print("🚀 Starting Plebbit daemon...")
    
    # Start daemon in background
    try:
        process = subprocess.Popen(['bitsocial', 'daemon'], 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                            text=True)
        
        # Give it time to start
        time.sleep(3)
        
        # Check if it's still running
        if process.poll() is None:
            print("✅ Plebbit daemon started successfully (PID: %s)" % process.pid)
            print("   Daemon running on: http://localhost:9138")
            print("   WebUI available at: http://localhost:9138/plebones")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Daemon failed to start: {stderr}")
            return None
            
    except FileNotFoundError:
        print("❌ 'bitsocial' command not found. Make sure it's installed and in PATH")
        return None

def check_daemon_status():
    """Check if daemon is running and show status"""
    try:
        import requests
        response = requests.get("http://localhost:9138/", timeout=5)
        if response.status_code == 200:
            print("✅ Plebbit daemon is running")
            return True
    except:
        print("❌ Plebbit daemon is not running")
        return False

async def demo_bridge():
    """Show what bridge can do once daemon is running"""
    print("\n🌉 P2P Bridge Demo")
    print("=" * 50)
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent_api'))
    
    try:
        from p2p_bridge_v2 import PlebbitBridge
        
        # Show bridge capabilities
        print("📡 Bridge API Endpoints:")
        print("   GET  http://localhost:8001/health")
        print("   GET  http://localhost:8001/subs") 
        print("   GET  http://localhost:8001/subs/{address}")
        print("   GET  http://localhost:8001/subs/{address}/posts")
        print("   GET  http://localhost:8001/posts/{cid}")
        
        print("\n🔧 Try these commands once daemon is running:")
        print("   curl http://localhost:8001/health")
        print("   curl http://localhost:8001/subs")
        print("   curl http://localhost:8001/subs/pleblore.eth/posts")
        
    except ImportError as e:
        print(f"❌ Failed to import bridge: {e}")
        print("   Make sure requirements are installed: pip install -r agent_api/requirements.txt")

def show_usage():
    """Show complete usage instructions"""
    print("""
🚀 PlebX P2P Bridge Setup & Demo

Usage:
  python3 demo_setup.py [command]

Commands:
  install     - Install Bitsocial CLI
  start       - Start Bitsocial daemon  
  status      - Check daemon status
  demo        - Show bridge API demo
  setup       - Full setup (install + start + demo)

Examples:
  python3 demo_setup.py install
  python3 demo_setup.py start
  python3 demo_setup.py status
  python3 demo_setup.py demo
  python3 demo_setup.py setup

Quick Start:
  1. python3 demo_setup.py setup
  2. Wait for daemon to start
  3. Open http://localhost:9138/plebones
  4. Test bridge at http://localhost:8001

For full documentation, see: BRIDGE_README.md
""")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "install":
        install_bitsocial_cli()
    elif command == "start":
        start_plebbit_daemon()
    elif command == "status":
        check_daemon_status()
    elif command == "demo":
        asyncio.run(demo_bridge())
    elif command == "setup":
        print("🔧 Full PlebX P2P Bridge Setup")
        print("-" * 40)
        
        # Install
        if not install_bitsocial_cli():
            print("❌ Setup failed at installation step")
            return
        
        # Start
        daemon_process = start_plebbit_daemon()
        if not daemon_process:
            print("❌ Setup failed at daemon start step")
            return
        
        # Demo capabilities
        print("\n⏳ Waiting for daemon to fully start...")
        time.sleep(5)
        asyncio.run(demo_bridge())
        
        print("\n🎉 Setup complete!")
        print("   P2P Bridge API: http://localhost:8001")
        print("   Bitsocial WebUI:  http://localhost:9138/plebones")
        print("   Documentation:    BRIDGE_README.md")
        
    else:
        print(f"❌ Unknown command: {command}")
        show_usage()

if __name__ == "__main__":
    main()