#!/usr/bin/env python3
import argparse
import random
import string
from pathlib import Path
from file_compressor import DirectoryCompressor
from create_test_directories import create_test_directory

def generate_random_text(length: int) -> str:
    """Generate random text content."""
    return ''.join(random.choices(string.ascii_letters + string.digits + '\n', k=length))

def create_test_directory(base_dir: Path, depth: int, max_depth: int, max_children: int):
    """Create a test directory structure with random files."""
    if depth > max_depth:
        return

    # Create random files in current directory
    num_files = random.randint(0, 10)
    for _ in range(num_files):
        file_path = base_dir / f"file_{random.randint(1000, 9999)}.txt"
        file_path.write_text(generate_random_text(random.randint(100, 1000)))

    # Create random subdirectories
    num_children = random.randint(0, max_children)
    for i in range(num_children):
        child_dir = base_dir / f"dir_{random.randint(1000, 9999)}"
        child_dir.mkdir(exist_ok=True)
        create_test_directory(child_dir, depth + 1, max_depth, max_children)

def main():
    parser = argparse.ArgumentParser(description="Storage Optimiser - Directory Management Tool")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Compression command
    compress_parser = subparsers.add_parser('compress', help='Compress directories')
    compress_parser.add_argument('directory', type=str, help='Directory to process')
    compress_parser.add_argument('--threshold', type=int, default=3000,
                               help='File count threshold for compression (default: 3000)')

    # Generate test directories command
    generate_parser = subparsers.add_parser('generate', help='Generate test directories')
    generate_parser.add_argument('directory', type=str,
                               help='Base directory for test data generation')
    generate_parser.add_argument('--max-children', type=int, default=3,
                               help='Maximum number of child directories per directory (default: 3)')
    generate_parser.add_argument('--max-depth', type=int, default=3,
                               help='Maximum depth of the directory tree (default: 3)')

    args = parser.parse_args()

    if args.command == 'compress':
        compressor = DirectoryCompressor(args.directory, args.threshold)
        success = compressor.process_directories()
        exit(0 if success else 1)
    
    elif args.command == 'generate':
        base_dir = Path(args.directory)
        base_dir.mkdir(exist_ok=True, parents=True)
        print(f"Generating test directory structure in {base_dir}")
        print(f"Max depth: {args.max_depth}, Max children per directory: {args.max_children}")
        create_test_directory(base_dir, 0, args.max_depth, args.max_children)
        print("Test directory structure created successfully!")
    
    else:
        parser.print_help()
        exit(1)

if __name__ == "__main__":
    main()