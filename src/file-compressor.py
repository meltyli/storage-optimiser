#!/usr/bin/env python3
import os
import sys
import shutil
import zipfile
import datetime

def count_files(directory):
    """Recursively count all files in the given directory."""
    count = 0
    for _, _, files in os.walk(directory):
        count += len(files)
    return count

def compress_directory(dir_path, output_zip):
    """Compress the entire directory (including nested folders) into a ZIP file."""
    with zipfile.ZipFile(output_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dir_path):
            for file in files:
                abs_file = os.path.join(root, file)
                # arcname makes sure the folder structure inside the zip starts from the t1 folder
                rel_path = os.path.relpath(abs_file, os.path.dirname(dir_path))
                zipf.write(abs_file, arcname=rel_path)
    return os.path.exists(output_zip)

def main(input_dir, threshold=3000):
    # Validate input directory
    if not os.path.isdir(input_dir):
        print(f"Error: '{input_dir}' is not a valid directory.")
        sys.exit(1)
    
    # Create .backups directory in input_dir if it doesn't exist
    backups_dir = os.path.join(input_dir, ".backups")
    os.makedirs(backups_dir, exist_ok=True)
    
    # Process each immediate subdirectory in the input_dir (excluding .backups)
    for entry in os.listdir(input_dir):
        t1_path = os.path.join(input_dir, entry)
        if os.path.isdir(t1_path) and entry != ".backups":
            num_files = count_files(t1_path)
            print(f"Directory '{entry}' contains {num_files} files.")
            if num_files >= threshold:
                # Build ZIP filename with a timestamp to ensure uniqueness
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                zip_filename = f"{entry}_{timestamp}.zip"
                zip_filepath = os.path.join(input_dir, zip_filename)
                print(f"Compressing '{entry}' into '{zip_filename}'...")
                try:
                    compress_directory(t1_path, zip_filepath)
                    print(f"Compression successful.")
                    # Move the original directory to the .backups directory
                    dest_path = os.path.join(backups_dir, entry)
                    # If a folder with that name already exists, append the timestamp
                    if os.path.exists(dest_path):
                        dest_path += f"_{timestamp}"
                    shutil.move(t1_path, dest_path)
                    print(f"Moved '{entry}' to backups folder.")
                except Exception as e:
                    print(f"Error processing '{entry}': {e}")
            else:
                print(f"Skipping '{entry}' (below threshold).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_archive.py <input_dir> [threshold]")
        sys.exit(1)
    input_directory = sys.argv[1]
    file_threshold = int(sys.argv[2]) if len(sys.argv) >= 3 else 3000
    main(input_directory, file_threshold)
