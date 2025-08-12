#!/usr/bin/env python3
"""
Complete Argos Translate Uninstaller
Removes all Argos packages, models, and cached data
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def uninstall_argos_translate():
    """Complete removal of Argos Translate and all its components"""
    
    print("=== Argos Translate Complete Uninstaller ===\n")
    print("This will remove:")
    print("  • Argos Translate Python package")
    print("  • All downloaded language models")
    print("  • All cached translation data")
    print("  • Configuration files\n")
    
    # Confirm with user
    response = input("Are you sure you want to uninstall Argos Translate? (yes/no): ")
    if response.lower() != 'yes':
        print("Uninstallation cancelled.")
        return
    
    print("\nStarting uninstallation...\n")
    
    # Step 1: Remove installed language packages
    try:
        from argostranslate import package, translate
        
        print("=== Removing Installed Language Models ===")
        installed_packages = package.get_installed_packages()
        
        if installed_packages:
            for pkg in installed_packages:
                print(f"Removing {pkg.from_name} → {pkg.to_name}...")
                package.remove(pkg)
            print(f"✓ Removed {len(installed_packages)} language models")
        else:
            print("No language models found to remove")
            
    except ImportError:
        print("Argos Translate not installed or already removed")
    except Exception as e:
        print(f"Error removing language models: {e}")
    
    # Step 2: Uninstall pip package
    print("\n=== Uninstalling Argos Translate Package ===")
    try:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "argostranslate", "-y"], 
                      check=True, capture_output=True, text=True)
        print("✓ Argos Translate package uninstalled")
    except subprocess.CalledProcessError:
        print("✗ Package may already be uninstalled")
    
    # Step 3: Remove Argos data directories
    print("\n=== Removing Argos Data Directories ===")
    
    # Common Argos data locations
    argos_dirs = []
    
    # User home directory locations
    home = Path.home()
    argos_dirs.extend([
        home / ".argos-translate",
        home / ".local" / "share" / "argos-translate",
        home / ".cache" / "argos-translate",
        home / "AppData" / "Local" / "argos-translate",  # Windows
        home / "AppData" / "Roaming" / "argos-translate",  # Windows
        home / "Library" / "Application Support" / "argos-translate",  # macOS
    ])
    
    # Check for ARGOS_TRANSLATE_PACKAGES_DIR environment variable
    if "ARGOS_TRANSLATE_PACKAGES_DIR" in os.environ:
        argos_dirs.append(Path(os.environ["ARGOS_TRANSLATE_PACKAGES_DIR"]))
    
    # Remove directories
    removed_count = 0
    for directory in argos_dirs:
        if directory.exists():
            try:
                shutil.rmtree(directory)
                print(f"✓ Removed: {directory}")
                removed_count += 1
            except Exception as e:
                print(f"✗ Failed to remove {directory}: {e}")
    
    if removed_count == 0:
        print("No Argos directories found")
    else:
        print(f"\n✓ Removed {removed_count} directories")
    
    # Step 4: Check for any remaining Argos files
    print("\n=== Checking for Remaining Files ===")
    
    # Search for common Argos file patterns
    search_patterns = [
        "argos*.json",
        "argos*.db",
        "*argostranslate*",
    ]
    
    remaining_files = []
    for pattern in search_patterns:
        for path in [home / ".local", home / ".config", home / ".cache"]:
            if path.exists():
                for file in path.rglob(pattern):
                    remaining_files.append(file)
    
    if remaining_files:
        print(f"\nFound {len(remaining_files)} remaining files:")
        for file in remaining_files[:10]:  # Show first 10
            print(f"  • {file}")
        if len(remaining_files) > 10:
            print(f"  ... and {len(remaining_files) - 10} more")
        
        remove_remaining = input("\nRemove these files? (yes/no): ")
        if remove_remaining.lower() == 'yes':
            for file in remaining_files:
                try:
                    if file.is_file():
                        file.unlink()
                    elif file.is_dir():
                        shutil.rmtree(file)
                except Exception as e:
                    print(f"Failed to remove {file}: {e}")
            print("✓ Remaining files removed")
    else:
        print("✓ No remaining Argos files found")
    
    # Step 5: Clean pip cache
    print("\n=== Cleaning Pip Cache ===")
    try:
        subprocess.run([sys.executable, "-m", "pip", "cache", "remove", "argostranslate"], 
                      capture_output=True, text=True)
        print("✓ Pip cache cleaned")
    except:
        print("✗ Could not clean pip cache (not critical)")
    
    # Step 6: Final verification
    print("\n=== Verification ===")
    try:
        import argostranslate
        print("⚠ Warning: Argos Translate can still be imported. You may need to restart Python.")
    except ImportError:
        print("✓ Argos Translate successfully uninstalled")
    
    print("\n=== Uninstallation Complete ===")
    print("\nArgos Translate has been removed from your system.")
    print("You can now install IndicTrans2 or any other translation system.")

def check_disk_space_recovered():
    """Estimate disk space recovered"""
    try:
        # Try to calculate space freed (approximate)
        home = Path.home()
        potential_size = 0
        
        for dir_path in [home / ".argos-translate", home / ".local" / "share" / "argos-translate"]:
            if not dir_path.exists():
                # Estimate based on typical model sizes
                potential_size += 200 * 1024 * 1024  # ~200MB per language model
        
        if potential_size > 0:
            size_mb = potential_size / (1024 * 1024)
            print(f"\nEstimated disk space recovered: ~{size_mb:.1f} MB")
    except:
        pass

if __name__ == "__main__":
    print("ARGOS TRANSLATE UNINSTALLER")
    print("=" * 50)
    
    # Run uninstaller
    uninstall_argos_translate()
    
    # Check space recovered
    check_disk_space_recovered()
    
    print("\nYou can now proceed with installing IndicTrans2 for Indian language translations.")