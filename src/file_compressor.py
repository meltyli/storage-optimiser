#!/usr/bin/env python3
import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime
import zipfile
from typing import Optional, Union, List, Tuple
from logging.handlers import RotatingFileHandler
from time import perf_counter
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

@dataclass
class FileEntry:
    """Data class to store file information for processing."""
    source_path: Path
    archive_path: Path
    size: int

class DirectoryCompressor:
    def __init__(self, input_dir: Union[str, Path], file_threshold: int = 3000):
        """
        Initialize the directory compressor with improved configuration.

        Args:
            input_dir (str|Path): Path to the input directory.
            file_threshold (int): Minimum number of files to trigger compression.
        """
        self.input_dir = Path(input_dir)
        self.file_threshold = file_threshold
        self.backup_dir = self.input_dir / '.backups'
        self.logger = self._setup_logger()
        self._file_cache = {}  # Cache for directory contents
        self._cache_lock = threading.Lock()
        self.BUFFER_SIZE = 1024 * 1024  # 1MB buffer for file operations

    def _setup_logger(self) -> logging.Logger:
        """
        Set up logging configuration using singleton pattern with rotation.
        """
        logger_name = 'DirectoryCompressor'
        logger = logging.getLogger(logger_name)
        
        if not logger.hasHandlers():
            logger.setLevel(logging.INFO)
            
            # Console handler with simplified format
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(message)s'))
            
            # Rotating file handler with size limit and backup count
            file_handler = RotatingFileHandler(
                'directory_compressor.log',
                maxBytes=10*1024*1024,  # 10MB
                backupCount=3
            )
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        
        return logger

    def _scan_directory(self, directory: Path) -> List[FileEntry]:
        """
        Scan directory and cache file information for reuse.
        
        Args:
            directory (Path): Directory to scan
        Returns:
            List[FileEntry]: List of file entries with paths and sizes
        """
        with self._cache_lock:
            if directory in self._file_cache:
                return self._file_cache[directory]

            files = []
            try:
                for root, _, filenames in os.walk(directory):
                    root_path = Path(root)
                    for filename in filenames:
                        file_path = root_path / filename
                        try:
                            # Get relative path or fallback to filename
                            try:
                                arc_path = file_path.relative_to(directory.parent)
                            except ValueError:
                                arc_path = file_path.name

                            if file_path.exists() and os.access(file_path, os.R_OK):
                                size = file_path.stat().st_size
                                files.append(FileEntry(file_path, arc_path, size))
                        except Exception as e:
                            self.logger.error(f"Error processing file {file_path}: {e}")

                self._file_cache[directory] = files
                return files
            except Exception as e:
                self.logger.error(f"Error scanning directory {directory}: {e}")
                raise

    def count_files(self, directory: Path) -> Tuple[int, int]:
        """
        Count files and total size using cached directory scan.
        
        Returns:
            Tuple[int, int]: (file count, total size in bytes)
        """
        files = self._scan_directory(directory)
        return len(files), sum(f.size for f in files)

    def compress_directory(self, directory: Path) -> tuple[bool, Optional[Path]]:
        """
        Compress directory with optimized memory usage and progress tracking.
        """
        start_time = perf_counter()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = directory.parent / f"{directory.name}_{timestamp}.zip"
        failed_files = []
        
        try:
            # Get cached file list
            files = self._scan_directory(directory)
            total_size = sum(f.size for f in files)
            processed_size = 0
            
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, 
                               compresslevel=6) as zipf:
                
                for file_entry in files:
                    try:
                        # Use buffered approach for large files
                        with open(file_entry.source_path, 'rb') as f:
                            with zipf.open(str(file_entry.archive_path), 'w') as dest:
                                shutil.copyfileobj(f, dest, self.BUFFER_SIZE)
                        
                        processed_size += file_entry.size
                        if processed_size % (100 * self.BUFFER_SIZE) == 0:  # Log progress every 100MB
                            progress = (processed_size / total_size) * 100
                            self.logger.info(f"Compression progress: {progress:.1f}%")
                            
                    except Exception as e:
                        failed_files.append(str(file_entry.source_path))
                        self.logger.error(f"Error adding file {file_entry.source_path} to zip: {e}")

            elapsed_time = perf_counter() - start_time
            self.logger.info(f"Compression completed in {elapsed_time:.2f}s")
            self.logger.info(f"Processed {total_size / (1024*1024):.2f} MB")

            if failed_files:
                self.logger.warning(f"Failed to add {len(failed_files)} files to zip")
                with open(f"failed_files_{timestamp}.log", 'w') as f:
                    f.write('\n'.join(failed_files))

            return True, zip_path
        except Exception as e:
            self.logger.error(f"Error compressing directory {directory}: {e}")
            if zip_path.exists():
                zip_path.unlink()  # Clean up partial zip file
            return False, None

    def backup_directory(self, directory: Path) -> tuple[bool, Optional[Path]]:
        """
        Backup directory with enhanced error handling and atomic operations.
        """
        try:
            self.backup_dir.mkdir(exist_ok=True, parents=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{directory.name}_{timestamp}"
            
            # Verify backup directory permissions
            if not os.access(self.backup_dir, os.W_OK):
                raise PermissionError(f"No write access to backup directory: {self.backup_dir}")
            
            # Use temporary directory name during move
            temp_backup_path = backup_path.with_suffix('.tmp')
            
            self.logger.info(f"Moving {directory} to backup location: {backup_path}")
            shutil.move(str(directory), str(temp_backup_path))
            temp_backup_path.rename(backup_path)  # Atomic rename
            
            return True, backup_path
        except Exception as e:
            self.logger.error(f"Error backing up directory {directory}: {e}")
            # Cleanup on failure
            if 'temp_backup_path' in locals() and temp_backup_path.exists():
                try:
                    shutil.move(str(temp_backup_path), str(directory))
                except Exception as cleanup_error:
                    self.logger.error(f"Failed to restore directory during backup failure: {cleanup_error}")
            return False, None

    def process_directories(self) -> bool:
        """
        Process directories with enhanced error handling and performance monitoring.
        """
        start_time = perf_counter()
        total_bytes_processed = 0
        success = True

        try:
            if not self.input_dir.exists():
                raise FileNotFoundError(f"Input directory {self.input_dir} does not exist")

            if not os.access(self.input_dir, os.R_OK | os.W_OK):
                raise PermissionError(f"Insufficient permissions for directory {self.input_dir}")

            for t1_dir in self.input_dir.iterdir():
                if not t1_dir.is_dir() or t1_dir.name.startswith('.'):
                    continue

                self.logger.info(f"Processing directory: {t1_dir}")
                try:
                    file_count, dir_size = self.count_files(t1_dir)
                    total_bytes_processed += dir_size
                    
                    self.logger.info(
                        f"Found {file_count} files in {t1_dir} "
                        f"(Size: {dir_size / (1024*1024):.2f} MB)"
                    )

                    if file_count > self.file_threshold:
                        self.logger.info(f"Directory {t1_dir} exceeds threshold; compressing...")
                        compress_success, zip_path = self.compress_directory(t1_dir)
                        
                        if compress_success and zip_path:
                            self.logger.info(f"Successfully compressed to {zip_path}")
                            backup_success, backup_path = self.backup_directory(t1_dir)
                            
                            if backup_success and backup_path:
                                self.logger.info(f"Successfully moved to {backup_path}")
                            else:
                                success = False
                                self.logger.error(f"Failed to backup {t1_dir}, but compression succeeded")
                        else:
                            success = False
                            self.logger.error(f"Failed to compress {t1_dir}")
                    else:
                        self.logger.info(f"Skipping {t1_dir} (below threshold)")
                except Exception as e:
                    success = False
                    self.logger.error(f"Error processing {t1_dir}: {e}")
                    continue

            elapsed_time = perf_counter() - start_time
            self.logger.info(f"Directory processing completed in {elapsed_time:.2f}s")
            self.logger.info(f"Total processed: {total_bytes_processed / (1024*1024):.2f} MB")
            return success
        except Exception as e:
            self.logger.error(f"Critical error processing directories: {e}")
            return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python auto_archive.py <input_directory> [file_threshold]")
        sys.exit(1)

    try:
        input_directory = sys.argv[1]
        file_threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
        
        if file_threshold <= 0:
            raise ValueError("Threshold must be positive")
            
        compressor = DirectoryCompressor(input_directory, file_threshold)
        success = compressor.process_directories()
        sys.exit(0 if success else 1)
    except ValueError as e:
        print(f"Error: Invalid threshold value: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()