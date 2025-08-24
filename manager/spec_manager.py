"""
Specification Manager

Handles verification and management of specification directory content.
"""

import os
import hashlib
import yaml
import re
from pathlib import Path
from datetime import datetime


class SpecManager:
    """Manages specification directory operations."""
    
    def __init__(self, spec_dir: str = "context/spec"):
        """
        Initialize the SpecManager.
        
        Args:
            spec_dir: Path to the specification directory
        """
        self.spec_dir = Path(spec_dir)
        self.base_path = Path(__file__).parent.parent / spec_dir

    def verify_content(self) -> dict:
        """
        Verify the content of the specification directory by looking at the split files, and comparing the hashes to the master file.
        
        Returns:
            dict: Status information about the specification directory
        """
    
    def verify_spec_directory(self) -> dict:
        """
        Verify the specification directory content.
        
        Returns:
            dict: Status information about the specification directory
        """
        # For now, return dummy data as requested
        # This will be replaced with actual verification logic later
        
        dummy_data = {
            "status": "healthy",
            "file_count": 42,
            "last_verified": datetime.now().isoformat(),
            "spec_version": "1.0.0",
            "total_size_mb": 15.7,
            "directories": [
                "000_MASTER",
                "100_SPLIT", 
                "200_INDEX"
            ],
            "critical_files": [
                "specification-document.md",
                "CONTENT_HASH.txt",
                "MANIFEST.yaml"
            ]
        }
        
        return dummy_data
    
    def verify_spec_slice(self, slice_file_path: str) -> dict:
        """
        Verify the content of a specification slice by comparing it against the SPEC_RAW.md file.
        
        Args:
            slice_file_path: Path to the slice file (relative to spec directory)
            
        Returns:
            dict: Verification result with status, expected hash, actual hash, and details
        """
        try:
            # Construct full paths
            slice_path = self.base_path / slice_file_path
            spec_raw_path = self.base_path / "000_MASTER" / "SPEC_RAW.md"
            
            # Check if files exist
            if not slice_path.exists():
                return {
                    "status": "error",
                    "error": f"Slice file not found: {slice_file_path}",
                    "expected_hash": None,
                    "actual_hash": None
                }
            
            if not spec_raw_path.exists():
                return {
                    "status": "error", 
                    "error": f"SPEC_RAW.md not found",
                    "expected_hash": None,
                    "actual_hash": None
                }
            
            # Read and parse slice file
            slice_content = slice_path.read_text(encoding='utf-8')
            slice_metadata = self._extract_slice_metadata(slice_content)
            
            if not slice_metadata:
                return {
                    "status": "error",
                    "error": "Could not extract metadata from slice file",
                    "expected_hash": None,
                    "actual_hash": None
                }
            
            # Extract content from SPEC_RAW.md within the character range
            spec_raw_content = spec_raw_path.read_text(encoding='utf-8')
            extracted_content = self._extract_content_from_range(
                spec_raw_content, 
                slice_metadata['range']['chars']
            )
            
            if extracted_content is None:
                return {
                    "status": "error",
                    "error": f"Invalid character range: {slice_metadata['range']['chars']}",
                    "expected_hash": None,
                    "actual_hash": None
                }
            
            # Remove metadata from slice content
            cleaned_slice_content = self._remove_metadata(slice_content)
            
            # Strip whitespace from both contents for comparison
            extracted_content = extracted_content.strip()
            cleaned_slice_content = cleaned_slice_content.strip()
            
            # Compute hashes
            expected_hash = self._compute_hash(extracted_content)
            actual_hash = self._compute_hash(cleaned_slice_content)
            
            # Compare hashes
            is_valid = expected_hash == actual_hash
            
            return {
                "status": "valid" if is_valid else "mismatch",
                "slice_file": slice_file_path,
                "slice_id": slice_metadata.get('slice_id', 'unknown'),
                "range": slice_metadata['range']['chars'],
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
                "is_valid": is_valid,
                "extracted_length": len(extracted_content),
                "cleaned_slice_length": len(cleaned_slice_content)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Verification failed: {str(e)}",
                "expected_hash": None,
                "actual_hash": None
            }
    
    def _extract_slice_metadata(self, content: str) -> dict:
        """
        Extract metadata from slice file content.
        
        Args:
            content: Content of the slice file
            
        Returns:
            dict: Extracted metadata including range information
        """
        try:
            # Split content by YAML frontmatter markers
            parts = content.split('---')
            if len(parts) < 3:
                return None
            
            # Parse YAML frontmatter (between first and second ---)
            yaml_content = parts[1].strip()
            metadata = yaml.safe_load(yaml_content)
            
            # Validate required fields
            if not metadata or 'range' not in metadata or 'chars' not in metadata['range']:
                return None
                
            return metadata
            
        except yaml.YAMLError:
            return None
    
    def _extract_content_from_range(self, content: str, char_range: list) -> str:
        """
        Extract content from text within a character range.
        
        Args:
            content: Full text content
            char_range: List with [start, end] character positions
            
        Returns:
            str: Extracted content within the range, or None if invalid
        """
        if len(char_range) != 2:
            return None
            
        start, end = char_range
        
        # Validate range
        if not isinstance(start, int) or not isinstance(end, int):
            return None
        if start < 0 or end > len(content) or start > end:
            return None
            
        # Extract content (exclusive end range)
        return content[start:end]
    
    def _remove_metadata(self, content: str) -> str:
        """
        Remove YAML frontmatter metadata from content.
        
        Args:
            content: Content that may contain YAML frontmatter
            
        Returns:
            str: Content with metadata removed
        """
        parts = content.split('---')
        if len(parts) >= 3:
            # Return content after the second --- (skip metadata)
            return ''.join(parts[2:])
        else:
            # No metadata found, return original content
            return content
    
    def _compute_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of content.
        
        Args:
            content: Text content to hash
            
        Returns:
            str: Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_spec_path(self) -> Path:
        """
        Get the full path to the specification directory.
        
        Returns:
            Path: Full path to the specification directory
        """
        return self.base_path
    
    def spec_directory_exists(self) -> bool:
        """
        Check if the specification directory exists.
        
        Returns:
            bool: True if directory exists, False otherwise
        """
        return self.base_path.exists() and self.base_path.is_dir()

    def slice_spec_by_headings(self, output_dir: str = None, source_file: str = None) -> dict:
        """
        Automatically slice a markdown file into sections based on headings.
        Always clears existing slice files before creating new ones.
        
        Args:
            output_dir: Directory to output slice files (defaults to 100_SPLIT)
            source_file: Path to source markdown file (defaults to SPEC_RAW.md)
            
        Returns:
            dict: Summary of slicing operation with file counts and status
        """
        try:
            # Determine output directory
            if output_dir is None:
                output_dir = self.base_path / "100_SPLIT"
            else:
                output_dir = Path(output_dir)
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Always clear existing slice files for simplicity
            existing_files = list(output_dir.glob("*.md"))
            if existing_files:
                print(f"Found {len(existing_files)} existing slice files in {output_dir}")
                print("Clearing existing slices...")
                for existing_file in existing_files:
                    existing_file.unlink()
                print(f"✓ Cleared {len(existing_files)} existing slice files")
            else:
                print(f"No existing slice files found in {output_dir}")
            
            # Determine source file path
            if source_file is None:
                spec_raw_path = self.base_path / "000_MASTER" / "SPEC_RAW.md"
            else:
                spec_raw_path = Path(source_file)
            
            if not spec_raw_path.exists():
                return {
                    "status": "error",
                    "error": f"Source file not found at {spec_raw_path}",
                    "files_created": 0,
                    "files_skipped": 0
                }
            
            spec_content = spec_raw_path.read_text(encoding='utf-8')
            
            # Detect headings and create slices
            slices = self._detect_headings_and_slices(spec_content)
            
            # Generate slice files
            files_created = 0
            
            for slice_info in slices:
                slice_file_path = output_dir / f"{slice_info['slice_id']}.md"
                
                # Generate slice content
                slice_content = self._generate_slice_content(spec_content, slice_info, str(spec_raw_path))
                
                # Write slice file
                slice_file_path.write_text(slice_content, encoding='utf-8')
                files_created += 1
            
            return {
                "status": "success",
                "files_created": files_created,
                "total_slices": len(slices),
                "output_directory": str(output_dir)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Slicing failed: {str(e)}",
                "files_created": 0
            }

    def _detect_headings_and_slices(self, content: str) -> list:
        """
        Detect markdown headings and create slice information.
        
        Args:
            content: Full markdown content
            
        Returns:
            list: List of slice information dictionaries
        """
        
        # Pattern to match numbered section headings: ## 1. Title
        # This works with standard Markdown numbered headings
        heading_pattern = r'^##\s+(\d+)\.\s+(.+)$'
        
        lines = content.split('\n')
        slices = []
        
        # Calculate cumulative character positions for each line
        line_positions = []
        current_pos = 0
        for line in lines:
            line_positions.append(current_pos)
            current_pos += len(line) + 1  # +1 for newline
        
        for i, line in enumerate(lines):
            match = re.match(heading_pattern, line.strip())
            if match:
                section_number = match.group(1)
                section_title = match.group(2).strip()
                
                # Debug output to see what's being detected
                # print(f"DEBUG: Detected section '{section_number}. {section_title}' at line {i+1}")
                
                # Calculate character position of this heading
                heading_start = line_positions[i]
                
                # Find the next section marker
                next_heading_start = len(content)
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    next_match = re.match(heading_pattern, next_line)
                    if next_match:
                        next_heading_start = line_positions[j]
                        break
                
                # Create slice info
                slice_info = {
                    'slice_id': self._generate_slice_id(section_number, section_title),
                    'section_number': section_number,
                    'section_title': section_title,
                    'start_pos': heading_start,
                    'end_pos': next_heading_start,  # Don't subtract 1, let the extraction handle boundaries
                    'headings': [f"{section_number}. {section_title}"]
                }
                
                slices.append(slice_info)
        
        return slices

    def _is_same_or_higher_level(self, current: str, next_section: str) -> bool:
        """
        Check if next_section is at the same level or higher than current.
        
        Args:
            current: Current section number (e.g., "1", "12.1")
            next_section: Next section number to compare
            
        Returns:
            bool: True if next_section is same level or higher
        """
        current_parts = current.split('.')
        next_parts = next_section.split('.')
        
        # Compare the first part (major section number)
        if len(current_parts) > 0 and len(next_parts) > 0:
            try:
                current_major = int(current_parts[0])
                next_major = int(next_parts[0])
                return next_major >= current_major
            except ValueError:
                return False
        
        return False

    def _generate_slice_id(self, section_number: str, section_title: str) -> str:
        """
        Generate a slice ID from section number and title.
        
        Args:
            section_number: Section number (e.g., "1", "12.1")
            section_title: Section title
            
        Returns:
            str: Generated slice ID
        """
        # Clean section title for filename
        clean_title = re.sub(r'[^\w\s-]', '', section_title.lower())
        clean_title = re.sub(r'\s+', '-', clean_title).strip('-')
        
        # Truncate title to reasonable length (max 50 chars)
        if len(clean_title) > 50:
            clean_title = clean_title[:50].rstrip('-')
        
        # Create a simple, short filename
        padded_number = section_number.replace('.', '-')
        
        return f"{padded_number:0>3}-{clean_title}"

    def _generate_slice_content(self, full_content: str, slice_info: dict, source_file: str = None) -> str:
        """
        Generate the complete content for a slice file.
        
        Args:
            full_content: Full source content
            slice_info: Slice information dictionary
            source_file: Path to source file for frontmatter
            
        Returns:
            str: Complete slice file content with frontmatter
        """
        # Extract the content for this slice
        slice_content = full_content[slice_info['start_pos']:slice_info['end_pos']]
        
        # Generate tags based on section title
        tags = self._generate_tags(slice_info['section_title'], slice_info['section_number'])
        
        # Determine source path for frontmatter
        if source_file is None:
            source_path = 'SPEC_RAW.md'
        else:
            # For frontmatter, just use the filename for cleaner metadata
            source_path_obj = Path(source_file)
            source_path = source_path_obj.name
        
        # Generate frontmatter
        frontmatter = {
            'source': source_path,
            'slice_id': slice_info['slice_id'],
            'range': {
                'chars': [slice_info['start_pos'], slice_info['end_pos']]
            },
            'checksum': self._compute_hash(slice_content),
            'headings': slice_info['headings'],
            'tags': tags
        }
        
        # Convert to YAML
        yaml_content = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        
        # Combine frontmatter and content
        return f"---\n{yaml_content}---\n\n{slice_content}"

    def _generate_tags(self, section_title: str, section_number: str) -> list:
        """
        Generate tags for a section based on title and number.
        
        Args:
            section_title: Section title
            section_number: Section number
            
        Returns:
            list: List of generated tags
        """
        tags = []
        
        # Add section number as tag
        tags.append(f"section-{section_number}")
        
        # Add common tags based on section number
        section_num = section_number.split('.')[0]
        if section_num == '1':
            tags.extend(['introduction', 'overview', 'problem-statement'])
        elif section_num == '2':
            tags.extend(['users', 'requirements'])
        elif section_num == '3':
            tags.extend(['goals', 'metrics', 'success-criteria'])
        elif section_num == '4':
            tags.extend(['non-goals', 'scope'])
        elif section_num == '5':
            tags.extend(['roles', 'decision-rights'])
        elif section_num == '6':
            tags.extend(['environments', 'deployment'])
        elif section_num == '7':
            tags.extend(['source-control', 'ci', 'github'])
        elif section_num == '8':
            tags.extend(['runtime', 'images', 'containers'])
        elif section_num == '9':
            tags.extend(['orchestration', 'messaging'])
        elif section_num == '10':
            tags.extend(['persistence', 'storage', 'database'])
        elif section_num == '11':
            tags.extend(['secrets', 'identity', 'security'])
        elif section_num == '12':
            tags.extend(['functional-specs', 'workflows'])
        elif section_num == '13':
            tags.extend(['task-model', 'canonical'])
        elif section_num == '14':
            tags.extend(['streams', 'events', 'redis'])
        elif section_num == '15':
            tags.extend(['supabase', 'schema', 'database'])
        elif section_num == '16':
            tags.extend(['api', 'rest', 'coordinator'])
        elif section_num == '17':
            tags.extend(['agent-contract', 'communication'])
        elif section_num == '18':
            tags.extend(['infrastructure', 'deployment'])
        elif section_num == '19':
            tags.extend(['performance', 'reliability'])
        elif section_num == '20':
            tags.extend(['scalability', 'growth'])
        elif section_num == '21':
            tags.extend(['security', 'privacy'])
        
        # Add tags based on title keywords
        title_lower = section_title.lower()
        if 'problem' in title_lower:
            tags.append('problem-statement')
        if 'users' in title_lower:
            tags.append('users')
        if 'goals' in title_lower:
            tags.append('goals')
        if 'non-goals' in title_lower:
            tags.append('non-goals')
        if 'roles' in title_lower:
            tags.append('roles')
        if 'environments' in title_lower:
            tags.append('environments')
        if 'source' in title_lower or 'ci' in title_lower:
            tags.append('source-control')
        if 'runtime' in title_lower or 'images' in title_lower:
            tags.append('runtime')
        if 'orchestration' in title_lower:
            tags.append('orchestration')
        if 'persistence' in title_lower or 'storage' in title_lower:
            tags.append('persistence')
        if 'secrets' in title_lower or 'identity' in title_lower:
            tags.append('secrets')
        if 'functional' in title_lower:
            tags.append('functional-specs')
        if 'task' in title_lower:
            tags.append('task-model')
        if 'streams' in title_lower or 'events' in title_lower:
            tags.append('streams')
        if 'supabase' in title_lower or 'schema' in title_lower:
            tags.append('supabase')
        if 'api' in title_lower or 'rest' in title_lower:
            tags.append('api')
        if 'agent' in title_lower or 'contract' in title_lower:
            tags.append('agent-contract')
        if 'infrastructure' in title_lower:
            tags.append('infrastructure')
        if 'performance' in title_lower:
            tags.append('performance')
        if 'scalability' in title_lower:
            tags.append('scalability')
        if 'security' in title_lower or 'privacy' in title_lower:
            tags.append('security')
        
        # Remove duplicates and return
        return list(set(tags))

    def verify_all_slices(self, verbose: bool = True) -> dict:
        """
        Verify all specification slices against the source SPEC_RAW.md file.
        
        Args:
            verbose: Whether to print detailed output during verification
            
        Returns:
            dict: Summary of verification results with counts and status
        """
        try:
            # Get all slice files
            slice_dir = self.base_path / "100_SPLIT"
            if not slice_dir.exists():
                if verbose:
                    print("❌ No 100_SPLIT directory found")
                return {
                    "status": "error",
                    "error": "No 100_SPLIT directory found",
                    "total_slices": 0,
                    "valid_count": 0,
                    "mismatch_count": 0,
                    "error_count": 0
                }
            
            slice_files = list(slice_dir.glob("*.md"))
            if not slice_files:
                if verbose:
                    print("❌ No slice files found in 100_SPLIT directory")
                return {
                    "status": "error",
                    "error": "No slice files found in 100_SPLIT directory",
                    "total_slices": 0,
                    "valid_count": 0,
                    "mismatch_count": 0,
                    "error_count": 0
                }
            
            if verbose:
                print(f"Found {len(slice_files)} slice files to verify")
                print()
            
            # Verify each slice
            valid_count = 0
            mismatch_count = 0
            error_count = 0
            verification_results = []
            
            for slice_file in sorted(slice_files):
                slice_path = slice_file.relative_to(self.base_path)
                if verbose:
                    print(f"Verifying {slice_path.name}...", end=" ")
                
                result = self.verify_spec_slice(str(slice_path))
                verification_results.append(result)
                
                if result['status'] == 'valid':
                    if verbose:
                        print("✅ VALID")
                    valid_count += 1
                elif result['status'] == 'mismatch':
                    if verbose:
                        print("❌ MISMATCH")
                        print(f"    Expected hash: {result['expected_hash'][:16]}...")
                        print(f"    Actual hash:   {result['actual_hash'][:16]}...")
                    mismatch_count += 1
                else:
                    if verbose:
                        print(f"❌ ERROR: {result.get('error', 'Unknown error')}")
                    error_count += 1
            
            if verbose:
                print()
                print("=" * 60)
                print("Verification Summary")
                print("=" * 60)
                print(f"Total slices: {len(slice_files)}")
                print(f"✅ Valid: {valid_count}")
                print(f"❌ Mismatch: {mismatch_count}")
                print(f"❌ Error: {error_count}")
                
                if mismatch_count == 0 and error_count == 0:
                    print("\n🎉 All slices verified successfully!")
                else:
                    print(f"\n❌ {mismatch_count + error_count} slices failed verification")
            
            # Return summary results
            overall_status = "success" if mismatch_count == 0 and error_count == 0 else "failed"
            
            return {
                "status": overall_status,
                "total_slices": len(slice_files),
                "valid_count": valid_count,
                "mismatch_count": mismatch_count,
                "error_count": error_count,
                "verification_results": verification_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Verification failed: {str(e)}"
            if verbose:
                print(f"❌ {error_msg}")
            
            return {
                "status": "error",
                "error": error_msg,
                "total_slices": 0,
                "valid_count": 0,
                "mismatch_count": 0,
                "error_count": 0,
                "verification_results": [],
                "timestamp": datetime.now().isoformat()
            }
