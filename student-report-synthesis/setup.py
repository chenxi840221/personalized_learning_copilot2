#!/usr/bin/env python3
"""
Setup script for the Student Report Generation System.
This script creates the necessary directory structure and files.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path


def create_directory_structure(base_dir="."):
    """Create the directory structure for the project."""
    print("Creating directory structure...")
    
    # Main directories
    directories = [
        "src",
        "src/report_engine",
        "src/report_engine/templates",
        "src/report_engine/styles",
        "src/report_engine/ai",
        "output",
        "templates",
        "static",
        "logs",
        "tests",
        "docs"
    ]
    
    for directory in directories:
        os.makedirs(os.path.join(base_dir, directory), exist_ok=True)
        print(f"  ✅ Created directory: {directory}")


def create_init_files(base_dir="."):
    """Create __init__.py files for Python packages."""
    print("Creating __init__.py files...")
    
    # Paths where __init__.py files should be created
    init_paths = [
        "src",
        "src/report_engine",
        "src/report_engine/templates",
        "src/report_engine/styles",
        "src/report_engine/ai",
        "tests"
    ]
    
    for path in init_paths:
        init_file = os.path.join(base_dir, path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                package_name = path.replace("/", ".").replace(".", "", 1) if path != "." else "student_report_system"
                f.write(f'"""\n{package_name} package.\n"""\n\n')
            print(f"  ✅ Created file: {init_file}")


def touch_file(filepath, content=""):
    """Create an empty file or file with content."""
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  ✅ Created file: {filepath}")


def create_placeholder_files(base_dir="."):
    """Create placeholder files in the directory structure."""
    print("Creating placeholder files...")
    
    # Create README files
    touch_file(os.path.join(base_dir, "output", "README.md"), 
               "# Output Directory\n\nGenerated reports will be stored in this directory.\n")
    
    touch_file(os.path.join(base_dir, "templates", "README.md"), 
               "# Templates Directory\n\nHTML templates for different report styles are stored here.\n")
    
    touch_file(os.path.join(base_dir, "static", "README.md"), 
               "# Static Directory\n\nStatic files like CSS, images, and JavaScript files are stored here.\n")
    
    touch_file(os.path.join(base_dir, "logs", "README.md"), 
               "# Logs Directory\n\nLog files are stored in this directory.\n")
    
    # Create a sample .env file
    touch_file(os.path.join(base_dir, ".env.example"), 
               "# Copy this file to .env and fill in your API keys\n"
               "OPENAI_ENDPOINT=https://your-openai.openai.azure.com/\n"
               "OPENAI_KEY=your-openai-key\n"
               "OPENAI_DEPLOYMENT=gpt-4o\n"
               "FORM_RECOGNIZER_ENDPOINT=https://your-form-recognizer.cognitiveservices.azure.com/\n"
               "FORM_RECOGNIZER_KEY=your-form-recognizer-key\n")


def copy_file_if_exists(src, dst):
    """Copy a file if it exists, create parent directories if needed."""
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  ✅ Copied file: {src} -> {dst}")
        return True
    else:
        print(f"  ❌ Source file doesn't exist: {src}")
        return False


def move_files_to_refactored_structure(base_dir="."):
    """Move existing files to the refactored structure."""
    print("Moving files to refactored structure...")
    
    # Map of old file locations to new file locations
    file_mapping = {
        "student_data_generator.py": "src/report_engine/student_data_generator.py",
        "report_styles.py": "src/report_engine/styles/report_styles.py",
        "ai_content_generator.py": "src/report_engine/ai/ai_content_generator.py",
        "enhanced_report_generator.py": "src/report_engine/enhanced_report_generator.py",
        "generate_reports.py": "generate_reports.py",
        "templates/act_template.html": "templates/act_template.html",
        "templates/nsw_template.html": "templates/nsw_template.html",
    }
    
    # Old files to deprecated (move to _deprecated directory)
    deprecated_files = [
        "main.py",
        "student_report_system.py",
        "azure-setup.sh",
        "deployment.sh",
        "run.sh",
        "connection-test.sh"
    ]
    
    # Create _deprecated directory
    os.makedirs(os.path.join(base_dir, "_deprecated"), exist_ok=True)
    
    # Move files according to mapping
    for old_path, new_path in file_mapping.items():
        src = os.path.join(base_dir, old_path)
        dst = os.path.join(base_dir, new_path)
        copy_file_if_exists(src, dst)
    
    # Move deprecated files
    for file in deprecated_files:
        src = os.path.join(base_dir, file)
        dst = os.path.join(base_dir, "_deprecated", file)
        copy_file_if_exists(src, dst)


def create_main_files(base_dir="."):
    """Create main Python files with imports adjusted for the new structure."""
    print("Creating main files...")
    
    # Create main.py that imports from the new structure
    main_py = '''#!/usr/bin/env python3
"""
Main entry point for the Student Report Generation System.
"""

import os
import logging
from dotenv import load_dotenv

from src.report_engine.enhanced_report_generator import EnhancedReportGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to run the report generator."""
    # Load environment variables
    load_dotenv()
    
    # Get API keys from environment variables
    openai_endpoint = os.environ.get("OPENAI_ENDPOINT", "")
    openai_key = os.environ.get("OPENAI_KEY", "")
    openai_deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")
    form_recognizer_endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT", "")
    form_recognizer_key = os.environ.get("FORM_RECOGNIZER_KEY", "")
    
    # Check if OpenAI credentials are set
    if not openai_endpoint or not openai_key:
        logger.error("OpenAI credentials are not set. Please set OPENAI_ENDPOINT and OPENAI_KEY environment variables.")
        return 1
    
    # Initialize the report generator
    report_generator = EnhancedReportGenerator(
        form_recognizer_endpoint=form_recognizer_endpoint,
        form_recognizer_key=form_recognizer_key,
        openai_endpoint=openai_endpoint,
        openai_key=openai_key,
        openai_deployment=openai_deployment,
        templates_dir="templates",
        output_dir="output",
        report_styles_dir="src/report_engine/styles"
    )
    
    # Generate a sample report
    output_path = report_generator.generate_report(
        style="act",
        output_format="pdf",
        comment_length="standard"
    )
    
    if output_path:
        logger.info(f"Report generated successfully: {output_path}")
        print(f"✅ Report generated successfully: {output_path}")
        return 0
    else:
        logger.error("Failed to generate report.")
        print("❌ Failed to generate report.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
    
    touch_file(os.path.join(base_dir, "main.py"), main_py)


def update_import_statements(base_dir="."):
    """Update import statements in Python files to reflect the new structure."""
    print("Updating import statements...")
    
    # Files to update
    files_to_update = [
        "src/report_engine/enhanced_report_generator.py",
        "generate_reports.py",
    ]
    
    # Import mappings (old -> new)
    import_mappings = {
        "from report_styles import": "from src.report_engine.styles.report_styles import",
        "from student_data_generator import": "from src.report_engine.student_data_generator import",
        "from ai_content_generator import": "from src.report_engine.ai.ai_content_generator import",
        "from enhanced_report_generator import": "from src.report_engine.enhanced_report_generator import",
    }
    
    for file_path in files_to_update:
        full_path = os.path.join(base_dir, file_path)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                content = f.read()
            
            # Update import statements
            for old_import, new_import in import_mappings.items():
                content = content.replace(old_import, new_import)
            
            with open(full_path, "w") as f:
                f.write(content)
            
            print(f"  ✅ Updated imports in: {file_path}")
        else:
            print(f"  ❌ File doesn't exist: {file_path}")


def setup_symlinks(base_dir="."):
    """Set up symlinks for backward compatibility."""
    print("Setting up symlinks for backward compatibility...")
    
    # Symlinks to create (old_path -> new_path)
    symlinks = {
        "student_data_generator.py": "src/report_engine/student_data_generator.py",
        "report_styles.py": "src/report_engine/styles/report_styles.py",
        "ai_content_generator.py": "src/report_engine/ai/ai_content_generator.py",
        "enhanced_report_generator.py": "src/report_engine/enhanced_report_generator.py",
    }
    
    for old_path, new_path in symlinks.items():
        old_full_path = os.path.join(base_dir, old_path)
        new_full_path = os.path.join(base_dir, new_path)
        
        # Remove old file if it exists
        if os.path.exists(old_full_path):
            os.remove(old_full_path)
        
        # Create relative path for symlink
        rel_path = os.path.relpath(new_full_path, os.path.dirname(old_full_path))
        
        # Create symlink if target exists
        if os.path.exists(new_full_path):
            try:
                os.symlink(rel_path, old_full_path)
                print(f"  ✅ Created symlink: {old_path} -> {rel_path}")
            except Exception as e:
                print(f"  ❌ Failed to create symlink: {old_path} -> {rel_path} ({str(e)})")
                # Create a simple import redirection file
                with open(old_full_path, "w") as f:
                    module_name = os.path.splitext(os.path.basename(old_path))[0]
                    f.write(f'"""\nImport redirection for backward compatibility.\n"""\n\n')
                    f.write(f'from {os.path.splitext(new_path)[0].replace("/", ".")} import *\n')
                print(f"  ✅ Created import redirection file: {old_path}")
        else:
            print(f"  ❌ Target file doesn't exist: {new_path}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Set up the Student Report Generation System")
    parser.add_argument("--dir", default=".", help="Base directory for the project")
    parser.add_argument("--clean", action="store_true", help="Clean existing files before setup")
    return parser.parse_args()


def clean_directories(base_dir=".", exclude=None):
    """Clean directories by removing all files and subdirectories."""
    if exclude is None:
        exclude = [".git", ".github", ".gitignore", ".env", "venv", "env", "__pycache__"]
    
    print("Cleaning directories...")
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        
        if os.path.isdir(item_path) and item not in exclude:
            try:
                shutil.rmtree(item_path)
                print(f"  ✅ Removed directory: {item}")
            except Exception as e:
                print(f"  ❌ Failed to remove directory: {item} ({str(e)})")
        elif os.path.isfile(item_path) and item not in exclude:
            try:
                os.remove(item_path)
                print(f"  ✅ Removed file: {item}")
            except Exception as e:
                print(f"  ❌ Failed to remove file: {item} ({str(e)})")


def main():
    """Main function to run the setup script."""
    args = parse_args()
    
    base_dir = args.dir
    
    # Create base directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    
    # Clean directories if requested
    if args.clean:
        clean_directories(base_dir)
    
    # Create directory structure
    create_directory_structure(base_dir)
    
    # Create __init__.py files
    create_init_files(base_dir)
    
    # Create placeholder files
    create_placeholder_files(base_dir)
    
    # Move existing files to the new structure
    move_files_to_refactored_structure(base_dir)
    
    # Update import statements
    update_import_statements(base_dir)
    
    # Create main files
    create_main_files(base_dir)
    
    # Set up symlinks for backward compatibility
    setup_symlinks(base_dir)
    
    print("\nSetup completed successfully! 🎉")
    print("\nTo generate a sample report, run:")
    print(f"  python {os.path.join(base_dir, 'main.py')}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())