#!/usr/bin/env python3
import os
import random
import argparse
import string

def create_random_text(length):
    """
    Generate a random string of the given length using letters, digits, and spaces.
    """
    characters = string.ascii_letters + string.digits + " "
    return ''.join(random.choices(characters, k=length))

def create_files_in_directory(directory, min_files=10, max_files=100):
    """
    Create a random number of text files in the given directory.
    Each file is filled with a short random string.
    """
    num_files = random.randint(min_files, max_files)
    for _ in range(num_files):
        file_name = f"file_{random.randint(10000, 99999)}.txt"
        file_path = os.path.join(directory, file_name)
        # Generate random content of length between 20 and 50 characters.
        content_length = random.randint(20, 50)
        content = create_random_text(content_length)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Created file: {file_path}")

def create_tree(base_path, max_children, max_depth, current_depth=0):
    """
    Create random files in the current directory, then create a random number of child directories.
    Recursively build the directory tree until the maximum depth is reached.
    """
    # Create random files in the current directory.
    create_files_in_directory(base_path)

    # Stop if we've reached the maximum depth.
    if current_depth >= max_depth:
        return

    # Determine the number of child directories (could be 0).
    num_children = random.randint(0, max_children)
    for _ in range(num_children):
        child_dir_name = f"child_{random.randint(10000, 99999)}"
        child_path = os.path.join(base_path, child_dir_name)
        os.mkdir(child_path)
        print(f"Created directory: {child_path}")
        # Recursively create the tree in the new child directory.
        create_tree(child_path, max_children, max_depth, current_depth + 1)

def main():
    parser = argparse.ArgumentParser(
        description="Create a directory tree with random nested child directories and random text files."
    )
    parser.add_argument(
        "base_directory",
        type=str,
        help="The base directory where the tree will be created. (Will be created if it doesn't exist.)"
    )
    parser.add_argument(
        "-c",
        "--max_children",
        type=int,
        default=3,
        help="Maximum number of child directories per directory (default: 3)"
    )
    parser.add_argument(
        "-d",
        "--max_depth",
        type=int,
        default=3,
        help="Maximum depth of the directory tree (default: 3)"
    )
    args = parser.parse_args()

    # Create the base directory if it doesn't exist.
    if not os.path.exists(args.base_directory):
        os.makedirs(args.base_directory)
        print(f"Created base directory: {args.base_directory}")

    create_tree(args.base_directory, args.max_children, args.max_depth)

if __name__ == "__main__":
    main()
