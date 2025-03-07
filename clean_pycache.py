"""
Script to recursively delete all __pycache__ directories in the project.
Run this script to clean up compiled Python files.
"""
import os
import shutil
import sys

def remove_pycache_folders(root_dir=None):
    """
    Remove all __pycache__ folders and .pyc files recursively starting from root_dir.
    If no root_dir is provided, use the current directory.
    """
    if root_dir is None:
        root_dir = os.path.dirname(os.path.abspath(__file__))
    
    count = 0
    size_cleaned = 0
    
    print(f"Searching for __pycache__ folders in {root_dir}...")
    
    # Walk through all directories under root_dir
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Check if __pycache__ is in current directories
        if '__pycache__' in dirnames:
            pycache_path = os.path.join(dirpath, '__pycache__')
            
            # Calculate size before deletion
            folder_size = sum(
                os.path.getsize(os.path.join(folder_path, filename))
                for folder_path, _, filenames in os.walk(pycache_path)
                for filename in filenames
            )
            
            # Delete the directory
            try:
                shutil.rmtree(pycache_path)
                count += 1
                size_cleaned += folder_size
                print(f"Removed: {pycache_path}")
            except Exception as e:
                print(f"Error removing {pycache_path}: {e}")
        
        # Remove .pyc files in all directories
        for filename in filenames:
            if filename.endswith('.pyc'):
                pyc_path = os.path.join(dirpath, filename)
                try:
                    file_size = os.path.getsize(pyc_path)
                    os.remove(pyc_path)
                    count += 1
                    size_cleaned += file_size
                    print(f"Removed: {pyc_path}")
                except Exception as e:
                    print(f"Error removing {pyc_path}: {e}")
    
    # Convert bytes to more readable format
    size_in_mb = size_cleaned / (1024 * 1024)
    
    print(f"\nCleanup complete!")
    print(f"Removed {count} __pycache__ directories and .pyc files")
    print(f"Freed up approximately {size_in_mb:.2f} MB of disk space")

if __name__ == "__main__":
    # Check if a custom directory was provided
    target_dir = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run the cleanup
    remove_pycache_folders(target_dir)
