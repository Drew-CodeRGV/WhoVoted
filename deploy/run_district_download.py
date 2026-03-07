#!/usr/bin/env python3
"""
Run the district download script on the server.
This connects via SSH and executes the download script.
"""

import subprocess
import sys

SERVER = "ubuntu@politiquera.com"

def run_ssh_command(command, description):
    """Run a command on the server via SSH."""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            ["ssh", SERVER, command],
            check=True,
            capture_output=False,
            text=True
        )
        print(f"\n✓ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {description} - FAILED")
        print(f"Error: {e}")
        return False
    except FileNotFoundError:
        print("\n✗ SSH command not found")
        print("Please ensure OpenSSH is installed")
        return False

def main():
    print("="*80)
    print("DOWNLOAD AND PARSE DISTRICT REFERENCE FILES")
    print("="*80)
    print(f"\nServer: {SERVER}")
    print()
    
    # Step 1: Pull latest code
    if not run_ssh_command(
        "cd /opt/whovoted && git pull",
        "Step 1: Pull latest code from GitHub"
    ):
        sys.exit(1)
    
    # Step 2: Make script executable
    if not run_ssh_command(
        "chmod +x /opt/whovoted/deploy/download_and_parse_districts.sh",
        "Step 2: Make script executable"
    ):
        sys.exit(1)
    
    # Step 3: Run the download script
    print("\n" + "="*80)
    print("Step 3: Running download and parse script")
    print("="*80)
    print("\nThis will take several minutes to download ~650MB...")
    print()
    
    if not run_ssh_command(
        "/opt/whovoted/deploy/download_and_parse_districts.sh",
        "Download and parse district files"
    ):
        sys.exit(1)
    
    print("\n" + "="*80)
    print("SUCCESS!")
    print("="*80)
    print()
    print("All district reference files have been:")
    print("  ✓ Downloaded from Texas Legislature")
    print("  ✓ Extracted from ZIP files")
    print("  ✓ Parsed into JSON files")
    print()
    print("The system can now reference these files for accurate district data!")
    print()

if __name__ == "__main__":
    main()
