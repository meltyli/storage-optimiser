#!/usr/bin/env python3
import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime
import zipfile

class DirectoryCompressor:
    def __init__(self, input_dir: str, file_threshold: int = 3000):
        """
        Initialize the directory compressor.

        Args:
            input_dir (str): Path to the input directory.
            file_threshold (int): Minimum number of files to trigger compression.
        """
        self.input_dir = Path(input_dir)
        self.file_threshold = file_threshold
        self.backup_dir = self.input_dir / '.backups'
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger('DirectoryCompressor')
        logger.setLevel(logging.INFO)

        # Avoid adding duplicate handlers if _setup_logger is called multiple times
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            file_handler = logging.FileHandler('directory_compressor.log')

            log_format = '%(asctime)s - %(levelname)s - %(message)s'
            formatter = logging.Formatter(log_format)
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        return logger

    def count_files(self, directory: Path) -> int:
        """
        Count total number of files in a directory (recursively).

        Args:
            directory (Path): Directory to count files in.
        Returns:
            int: Total number of files.
        """
        count = 0
        try:
            for _, _, files in os.walk(directory):
                count += len(files)
            return count
        except Exception as e:
            self.logger.error(f"Error counting files in {directory}: {e}")
            return 0

    def compress_directory(self, directory: Path) -> bool:
        """
        Compress the given directory (including nested directories) into a ZIP file.

        The resulting ZIP file will be placed in the parent of the tier‑1 directory,
        with a timestamp appended to its name.

        Args:
            directory (Path): Directory to compress.
        Returns:
            bool: True if compression was successful, False otherwise.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Place the zip file in the input directory (same level as tier-1 folder)
            zip_path = directory.parent / f"{directory.name}_{timestamp}.zip"
            self.logger.info(f"Creating ZIP: {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
                # Walk the directory and add files; preserve folder structure
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = Path(root) / file
                        # Use relative path starting at the input directory
                        try:
                            arc_path = file_path.relative_to(directory.parent)
                        except ValueError:
                            # Fallback: use the file name only
                            arc_path = file_path.name
                        try:
                            zipf.write(file_path, arc_path)
                        except Exception as e:
                            self.logger.error(f"Error adding file {file_path} to zip: {e}")
                            continue
            return True
        except Exception as e:
            self.logger.error(f"Error compressing directory {directory}: {e}")
            return False

    def backup_directory(self, directory: Path) -> bool:
        """
        Move the given directory to the backup (.backups) folder within the input directory.

        The backup directory will be created if it does not exist, and a timestamp is
        appended to the moved directory’s name.
        
        Args:
            directory (Path): Directory to back up.
        Returns:
            bool: True if the backup move was successful, False otherwise.
        """
        try:
            self.backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{directory.name}_{timestamp}"
            self.logger.info(f"Moving {directory} to backup location: {backup_path}")
            shutil.move(str(directory), str(backup_path))
            return True
        except Exception as e:
            self.logger.error(f"Error backing up directory {directory}: {e}")
            return False

    def process_directories(self):
        """Process all immediate (tier 1) subdirectories in the input directory."""
        try:
            if not self.input_dir.exists():
                raise FileNotFoundError(f"Input directory {self.input_dir} does not exist")

            for t1_dir in self.input_dir.iterdir():
                # Skip non-directories and hidden directories (like .backups)
                if not t1_dir.is_dir() or t1_dir.name.startswith('.'):
                    continue

                self.logger.info(f"Processing directory: {t1_dir}")
                file_count = self.count_files(t1_dir)
                self.logger.info(f"Found {file_count} files in {t1_dir}")

                if file_count > self.file_threshold:
                    self.logger.info(f"Directory {t1_dir} exceeds threshold; compressing...")
                    if self.compress_directory(t1_dir):
                        self.logger.info(f"Successfully compressed {t1_dir}")
                        if self.backup_directory(t1_dir):
                            self.logger.info(f"Successfully moved {t1_dir} to backups.")
                        else:
                            self.logger.error(f"Failed to backup {t1_dir}.")
                    else:
                        self.logger.error(f"Failed to compress {t1_dir}.")
                else:
                    self.logger.info(f"Skipping {t1_dir} (below threshold).")
        except Exception as e:
            self.logger.error(f"Error processing directories: {e}")

def main():
    # Example usage: adjust the input directory and threshold as needed
    if len(sys.argv) < 2:
        print("Usage: python auto_archive.py <input_directory> [file_threshold]")
        sys.exit(1)

    input_directory = sys.argv[1]
    file_threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

    compressor = DirectoryCompressor(input_directory, file_threshold)
    compressor.process_directories()

if __name__ == "__main__":
    main()
