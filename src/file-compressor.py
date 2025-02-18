import os
import sys
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
import logging
from typing import Optional, Union

class DirectoryCompressor:
    def __init__(self, input_dir: Union[str, Path], threshold: int = 3000):
        """Initialize the directory compressor.
        
        Args:
            input_dir: Path to the input directory
            threshold: Minimum number of files to trigger compression
        """
        self.input_dir = Path(input_dir)
        self.threshold = threshold
        self.backup_dir = self.input_dir / '.backups'
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Set up console and file logging."""
        logger = logging.getLogger('DirectoryCompressor')
        logger.setLevel(logging.INFO)
        
        # Create console handler with a more concise format
        console_handler = logging.StreamHandler()
        console_format = '%(message)s'
        console_handler.setFormatter(logging.Formatter(console_format))
        
        # Create file handler with detailed format
        file_handler = logging.FileHandler('directory_compressor.log')
        file_format = '%(asctime)s - %(levelname)s - %(message)s'
        file_handler.setFormatter(logging.Formatter(file_format))
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        return logger

    def count_files(self, directory: Path) -> int:
        """Recursively count all files in the given directory."""
        try:
            count = 0
            for _, _, files in os.walk(directory):
                count += len(files)
            return count
        except Exception as e:
            self.logger.error(f"Error counting files in {directory}: {e}")
            return 0

    def compress_directory(self, dir_path: Path, output_zip: Path) -> bool:
        """Compress the entire directory into a ZIP file."""
        try:
            with zipfile.ZipFile(output_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        abs_file = Path(root) / file
                        # Use relative path from parent directory for cleaner structure
                        rel_path = abs_file.relative_to(dir_path.parent)
                        zipf.write(abs_file, arcname=rel_path)
            return output_zip.exists()
        except Exception as e:
            self.logger.error(f"Error compressing directory: {e}")
            return False

    def backup_directory(self, source: Path, timestamp: str) -> Optional[Path]:
        """Move directory to backup location with timestamp if needed."""
        try:
            self.backup_dir.mkdir(exist_ok=True)
            dest_path = self.backup_dir / source.name
            
            # Append timestamp if destination already exists
            if dest_path.exists():
                dest_path = self.backup_dir / f"{source.name}_{timestamp}"
            
            shutil.move(str(source), str(dest_path))
            return dest_path
        except Exception as e:
            self.logger.error(f"Error backing up directory: {e}")
            return None

    def process_directories(self):
        """Process all tier 1 directories in the input directory."""
        if not self.input_dir.exists():
            self.logger.error(f"Error: '{self.input_dir}' is not a valid directory.")
            return False

        for entry in self.input_dir.iterdir():
            if not entry.is_dir() or entry.name == '.backups':
                continue

            num_files = self.count_files(entry)
            self.logger.info(f"Directory '{entry.name}' contains {num_files} files.")

            if num_files >= self.threshold:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                zip_filename = f"{entry.name}_{timestamp}.zip"
                zip_path = self.input_dir / zip_filename

                self.logger.info(f"Compressing '{entry.name}' into '{zip_filename}'...")
                if self.compress_directory(entry, zip_path):
                    self.logger.info("Compression successful.")
                    if self.backup_directory(entry, timestamp):
                        self.logger.info(f"Moved '{entry.name}' to backups folder.")
                    else:
                        self.logger.error(f"Failed to backup '{entry.name}'")
                else:
                    self.logger.error(f"Failed to compress '{entry.name}'")
            else:
                self.logger.info(f"Skipping '{entry.name}' (below threshold).")

        return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python directory_compressor.py <input_dir> [threshold]")
        sys.exit(1)

    input_directory = sys.argv[1]
    file_threshold = int(sys.argv[2]) if len(sys.argv) >= 3 else 3000

    compressor = DirectoryCompressor(input_directory, file_threshold)
    if not compressor.process_directories():
        sys.exit(1)

if __name__ == "__main__":
    main()