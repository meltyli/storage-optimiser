import os
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
            input_dir (str): Path to the input directory
            file_threshold (int): Minimum number of files to trigger compression
        """
        self.input_dir = Path(input_dir)
        self.file_threshold = file_threshold
        self.backup_dir = self.input_dir / '.backups'
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger('DirectoryCompressor')
        logger.setLevel(logging.INFO)
        
        # Create handlers
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler('directory_compressor.log')
        
        # Create formatters and add it to handlers
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger

    def count_files(self, directory: Path) -> int:
        """
        Count total number of files in a directory and its subdirectories.
        
        Args:
            directory (Path): Directory to count files in
            
        Returns:
            int: Total number of files
        """
        try:
            count = 0
            for root, _, files in os.walk(directory):
                count += len(files)
            return count
        except Exception as e:
            self.logger.error(f"Error counting files in {directory}: {str(e)}")
            return 0

    def compress_directory(self, directory: Path) -> bool:
        """
        Compress a directory into a zip file.
        
        Args:
            directory (Path): Directory to compress
            
        Returns:
            bool: True if compression was successful, False otherwise
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_path = directory.parent / f"{directory.name}_{timestamp}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = Path(root) / file
                        arc_path = file_path.relative_to(directory.parent)
                        try:
                            zipf.write(file_path, arc_path)
                        except Exception as e:
                            self.logger.error(f"Error adding file {file_path} to zip: {str(e)}")
                            continue
            
            return True
        except Exception as e:
            self.logger.error(f"Error compressing directory {directory}: {str(e)}")
            return False

    def backup_directory(self, directory: Path) -> bool:
        """
        Move a directory to the backup location.
        
        Args:
            directory (Path): Directory to backup
            
        Returns:
            bool: True if backup was successful, False otherwise
        """
        try:
            # Create backup directory if it doesn't exist
            self.backup_dir.mkdir(exist_ok=True)
            
            # Move directory to backup location
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{directory.name}_{timestamp}"
            shutil.move(str(directory), str(backup_path))
            
            return True
        except Exception as e:
            self.logger.error(f"Error backing up directory {directory}: {str(e)}")
            return False

    def process_directories(self):
        """Process all tier 1 directories in the input directory."""
        try:
            # Ensure input directory exists
            if not self.input_dir.exists():
                raise FileNotFoundError(f"Input directory {self.input_dir} does not exist")

            # Process each tier 1 directory
            for t1_dir in self.input_dir.iterdir():
                if not t1_dir.is_dir() or t1_dir.name.startswith('.'):
                    continue

                self.logger.info(f"Processing directory: {t1_dir}")
                
                # Count files
                file_count = self.count_files(t1_dir)
                self.logger.info(f"Found {file_count} files in {t1_dir}")
                
                if file_count > self.file_threshold:
                    self.logger.info(f"Compressing {t1_dir} ({file_count} files)")
                    
                    # Compress directory
                    if self.compress_directory(t1_dir):
                        self.logger.info(f"Successfully compressed {t1_dir}")
                        
                        # Backup original directory
                        if self.backup_directory(t1_dir):
                            self.logger.info(f"Successfully backed up {t1_dir}")
                        else:
                            self.logger.error(f"Failed to backup {t1_dir}")
                    else:
                        self.logger.error(f"Failed to compress {t1_dir}")

        except Exception as e:
            self.logger.error(f"Error processing directories: {str(e)}")

def main():
    # Example usage
    input_directory = "input_dir"  # Replace with your input directory path
    file_threshold = 3000  # Adjust this threshold as needed
    
    compressor = DirectoryCompressor(input_directory, file_threshold)
    compressor.process_directories()

if __name__ == "__main__":
    main()