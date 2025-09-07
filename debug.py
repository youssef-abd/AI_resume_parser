#!/usr/bin/env python3
"""
Comprehensive Debug Script for Streamlit App Issues
Run this to diagnose environment, dependencies, and configuration problems
"""

import sys
import os
import subprocess
import json
import traceback
from pathlib import Path
import importlib.util

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def run_command(cmd, description):
    """Run a command and return output"""
    try:
        print(f"\n[RUNNING] {description}")
        print(f"Command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        return result
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {cmd}")
        return None
    except Exception as e:
        print(f"Error running command: {e}")
        return None

def check_python_package(package_name, import_name=None):
    """Check if a Python package is installed and importable"""
    if import_name is None:
        import_name = package_name
    
    try:
        # Check if package is installed via pip
        result = subprocess.run([sys.executable, "-m", "pip", "show", package_name], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version_line = [line for line in result.stdout.split('\n') if line.startswith('Version:')]
            version = version_line[0].split(': ')[1] if version_line else 'Unknown'
            print(f"✅ {package_name} v{version} - installed")
        else:
            print(f"❌ {package_name} - not installed via pip")
            
        # Check if importable
        try:
            __import__(import_name)
            print(f"✅ {import_name} - importable")
        except ImportError as e:
            print(f"❌ {import_name} - import error: {e}")
            
    except Exception as e:
        print(f"❌ Error checking {package_name}: {e}")

def check_file_exists(filepath, description):
    """Check if a file exists and show its size"""
    path = Path(filepath)
    if path.exists():
        if path.is_file():
            size = path.stat().st_size
            print(f"✅ {description}: {filepath} ({size} bytes)")
            return True
        else:
            print(f"⚠️  {description}: {filepath} exists but is not a file")
    else:
        print(f"❌ {description}: {filepath} does not exist")
    return False

def check_directory_contents(dirpath, description):
    """List contents of a directory"""
    path = Path(dirpath)
    if path.exists() and path.is_dir():
        print(f"✅ {description}: {dirpath}")
        try:
            contents = list(path.iterdir())
            if contents:
                for item in sorted(contents)[:10]:  # Show first 10 items
                    print(f"   - {item.name}")
                if len(contents) > 10:
                    print(f"   ... and {len(contents) - 10} more items")
            else:
                print("   (empty directory)")
        except PermissionError:
            print("   (permission denied)")
    else:
        print(f"❌ {description}: {dirpath} does not exist or is not a directory")

def test_streamlit_import():
    """Test Streamlit import and basic functionality"""
    try:
        import streamlit as st
        print(f"✅ Streamlit version: {st.__version__}")
        
        # Check if streamlit command is available
        result = subprocess.run([sys.executable, "-m", "streamlit", "version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Streamlit CLI available")
            print(f"CLI output: {result.stdout.strip()}")
        else:
            print(f"❌ Streamlit CLI error: {result.stderr}")
            
    except ImportError as e:
        print(f"❌ Cannot import Streamlit: {e}")
    except Exception as e:
        print(f"❌ Streamlit test error: {e}")

def check_ports():
    """Check if required ports are available"""
    try:
        import socket
        ports_to_check = [8000, 8501, 7860]
        
        for port in ports_to_check:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"⚠️  Port {port} is in use")
            else:
                print(f"✅ Port {port} is available")
            sock.close()
    except Exception as e:
        print(f"❌ Error checking ports: {e}")

def check_environment_variables():
    """Check relevant environment variables"""
    env_vars = [
        'STREAMLIT_SERVER_PORT',
        'STREAMLIT_SERVER_HEADLESS', 
        'STREAMLIT_BROWSER_GATHER_USAGE_STATS',
        'PATH',
        'PYTHONPATH',
        'HOME',
        'USER'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        if var == 'PATH':
            # Show first 200 chars of PATH
            value = value[:200] + '...' if len(value) > 200 else value
        print(f"{var}: {value}")

def test_minimal_streamlit_app():
    """Create and test a minimal Streamlit app"""
    minimal_app = '''
import streamlit as st
import sys

print("MINIMAL APP: Starting...")
st.write("# Debug Test App")
st.write("✅ Streamlit is working!")
st.write(f"Python version: {sys.version}")
print("MINIMAL APP: Loaded successfully!")
'''
    
    try:
        with open('/tmp/minimal_debug_app.py', 'w') as f:
            f.write(minimal_app)
        print("✅ Created minimal test app at /tmp/minimal_debug_app.py")
        
        # Try to validate the Python syntax
        try:
            compile(minimal_app, '/tmp/minimal_debug_app.py', 'exec')
            print("✅ Minimal app syntax is valid")
        except SyntaxError as e:
            print(f"❌ Syntax error in minimal app: {e}")
            
    except Exception as e:
        print(f"❌ Error creating minimal app: {e}")

def main():
    """Main debug function"""
    print("🔍 STREAMLIT DEBUG SCRIPT")
    print(f"Timestamp: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}")
    
    # System Information
    print_section("SYSTEM INFORMATION")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"User: {os.environ.get('USER', 'Unknown')}")
    
    # Environment Variables
    print_section("ENVIRONMENT VARIABLES")
    check_environment_variables()
    
    # Python Packages
    print_section("PYTHON PACKAGES")
    packages_to_check = [
        ('streamlit', 'streamlit'),
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('requests', 'requests'),
    ]
    
    for pkg, import_name in packages_to_check:
        check_python_package(pkg, import_name)
    
    # File System Checks
    print_section("FILE SYSTEM CHECKS")
    files_to_check = [
        ('/app', 'App directory'),
        ('/app/app.py', 'Main Streamlit app'),
        ('/app/main.py', 'FastAPI main'),
        ('/app/requirements.txt', 'Requirements file'),
        ('/app/.streamlit/config.toml', 'Streamlit config'),
        ('/tmp/nginx.conf', 'Nginx config'),
    ]
    
    for filepath, description in files_to_check:
        if filepath.endswith('/'):
            check_directory_contents(filepath[:-1], description)
        else:
            check_file_exists(filepath, description)
    
    # Show app directory contents
    print_section("APP DIRECTORY CONTENTS")
    check_directory_contents('/app', 'Application root')
    
    # Network/Ports
    print_section("NETWORK & PORTS")
    check_ports()
    
    # Streamlit Specific Tests
    print_section("STREAMLIT TESTS")
    test_streamlit_import()
    test_minimal_streamlit_app()
    
    # Process Information
    print_section("RUNNING PROCESSES")
    run_command("ps aux | grep -E '(streamlit|uvicorn|nginx)' | grep -v grep", "Check running services")
    
    # System Resources
    print_section("SYSTEM RESOURCES")
    run_command("df -h", "Disk space")
    run_command("free -m", "Memory usage")
    
    # Network Connectivity
    print_section("NETWORK CONNECTIVITY")
    run_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8501/_stcore/health", "Streamlit health check")
    run_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health", "FastAPI health check")
    
    # Log Files
    print_section("LOG ANALYSIS")
    # Check if there are any recent Python error logs
    run_command("find /tmp -name '*.log' -mtime -1 2>/dev/null | head -5", "Recent log files")
    
    print_section("DEBUG COMPLETE")
    print("🏁 Debug script finished!")
    
    if is_container:
        print("\nTo run the minimal test app:")
        print("streamlit run /tmp/minimal_debug_app.py --server.port=8502")
    else:
        print("\n📋 SUMMARY FOR LOCAL WINDOWS ENVIRONMENT:")
        print("- This appears to be a local development environment")
        print("- To debug the actual deployed app, run this script inside the container")
        print("- To test Streamlit locally, try: streamlit run your_app.py")
        
        temp_file = os.path.join(os.environ.get('TEMP', '.'), 'minimal_debug_app.py')
        if os.path.exists(temp_file):
            print(f"- Test the minimal app with: streamlit run {temp_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Debug script interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Debug script error: {e}")
        print(traceback.format_exc())