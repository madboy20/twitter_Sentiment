#!/usr/bin/env python3
"""
Setup script for Twitter Sentiment Analysis System
"""

import os
import sys
import subprocess
from pathlib import Path

def install_requirements():
    """Install required Python packages."""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error installing requirements: {e}")
        return False
    return True

def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from template...")
        env_file.write_text(env_example.read_text())
        print("✓ .env file created")
        print("⚠️  Please edit .env file with your actual configuration values")
    elif env_file.exists():
        print("✓ .env file already exists")
    else:
        print("✗ .env.example not found")

def create_log_directory():
    """Create logs directory if it doesn't exist."""
    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir()
        print("✓ Logs directory created")
    else:
        print("✓ Logs directory already exists")

def validate_python_version():
    """Validate Python version."""
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def main():
    """Main setup function."""
    print("Twitter Sentiment Analysis System Setup")
    print("=" * 40)
    
    # Validate Python version
    if not validate_python_version():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Create configuration files
    create_env_file()
    
    # Create directories
    create_log_directory()
    
    print("\n" + "=" * 40)
    print("Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your configuration")
    print("2. Update followed_accounts.txt with accounts to monitor")
    print("3. Ensure your InfluxDB is running and accessible")
    print("4. Test the system: python main.py --run-now")
    print("5. Start the scheduler: python main.py")

if __name__ == "__main__":
    main()