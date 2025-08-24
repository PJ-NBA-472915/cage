#!/usr/bin/env python3
"""
Memory Bank Manager Service

A lightweight service for managing the memory-bank directory.
"""

import sys
import os
import argparse
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from manager.spec_manager import SpecManager
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    sys.exit(1)


def main():
    """Main entry point for the Memory Bank Manager."""
    parser = argparse.ArgumentParser(description="Memory Bank Manager Service")
    parser.add_argument('--slice', action='store_true', 
                       help='Slice SPEC_RAW.md into sections based on headings')
    parser.add_argument('--output-dir', type=str, 
                       help='Output directory for slice files (defaults to 100_SPLIT)')
    parser.add_argument('--source-file', type=str,
                       help='Source markdown file to slice (defaults to context/spec/000_MASTER/SPEC_RAW.md)')

    parser.add_argument('--verify', action='store_true',
                       help='Verify existing slice files')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Memory Bank Manager Service")
    print("=" * 60)
    
    # Initialize the spec manager
    spec_manager = SpecManager()
    
    if args.slice:
        source_file = args.source_file or "context/spec/000_MASTER/SPEC_RAW.md"
        print(f"\nSlicing {source_file} into sections...")
        slice_result = spec_manager.slice_spec_by_headings(
            output_dir=args.output_dir,
            source_file=args.source_file
        )
        
        if slice_result['status'] == 'success':
            print(f"✓ Slicing completed successfully!")
            print(f"  Files created: {slice_result['files_created']}")
            print(f"  Total slices: {slice_result['total_slices']}")
            print(f"  Output directory: {slice_result['output_directory']}")
        else:
            print(f"✗ Slicing failed: {slice_result['error']}")
            sys.exit(1)
    
    elif args.verify:
        print("\nVerifying specification slices...")
        # This would integrate with the existing verification system
        print("Verification functionality coming soon...")
    
    else:
        # Default behavior - verify specification directory content
        print("\nVerifying specification directory content...")
        spec_status = spec_manager.verify_spec_directory()
        
        print(f"Specification directory status: {spec_status['status']}")
        print(f"Files found: {spec_status['file_count']}")
        print(f"Last verified: {spec_status['last_verified']}")
    
    print("\n" + "=" * 60)
    print("Memory Bank Manager completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
