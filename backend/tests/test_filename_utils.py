import sys
import os
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.filename_utils import extract_student_name_from_filename, clean_student_name

class TestFilenameUtils(unittest.TestCase):
    """Test the filename utilities for student name extraction."""
    
    def test_clean_student_name(self):
        """Test the clean_student_name function."""
        test_cases = [
            # Test Student: prefix removal
            ("Student: John Smith", "John Smith"),
            ("student:John Smith", "John Smith"),
            ("Student : Mary Johnson", "Mary Johnson"),
            
            # Test capitalization
            ("john smith", "John Smith"),
            ("JOHN SMITH", "John Smith"),
            
            # Test separator removal
            ("John_Smith", "John Smith"),
            ("John-Smith", "John Smith"),
            ("John.Smith", "John Smith"),
            
            # Test whitespace handling
            ("  John   Smith  ", "John Smith"),
            
            # Test non-alphabetic removal
            ("John123 Smith456", "John Smith"),
            ("John Smith Jr.", "John Smith Jr"),
            
            # Test apostrophes
            ("O'Brien", "O'Brien"),
            
            # Test with multiple issues
            ("Student: john_smith-123", "John Smith"),
            
            # Edge cases
            ("", ""),
            (None, ""),
        ]
        
        for input_name, expected_output in test_cases:
            with self.subTest(input_name=input_name):
                self.assertEqual(clean_student_name(input_name), expected_output)
    
    def test_extract_student_name_from_filename(self):
        """Test the extract_student_name_from_filename function."""
        test_cases = [
            # Test basic patterns
            ("JohnSmith_Report.pdf", "John Smith"),
            ("Report_JohnSmith.pdf", "John Smith"),
            ("JohnSmith Report.pdf", "John Smith"),
            ("Report for JohnSmith.pdf", "John Smith"),
            ("JohnSmith.pdf", "John Smith"),
            
            # Test Student: prefix in filename
            ("Student_JohnSmith.pdf", "John Smith"),
            ("Student-JohnSmith.pdf", "John Smith"),
            ("Student: JohnSmith.pdf", "John Smith"),
            
            # Test firstname_lastname pattern
            ("Smith_John.pdf", "John Smith"),
            
            # Test with various delimiters
            ("Report-JohnSmith.pdf", "John Smith"),
            ("Report - JohnSmith.pdf", "John Smith"),
            ("JohnSmith - Report.pdf", "John Smith"),
            
            # Test complex patterns
            ("2023_Term1_JohnSmith_Report.pdf", "John Smith"),
            ("Class_JohnSmith_Math.pdf", "John Smith"),
            ("Grade_5_JohnSmith.pdf", "John Smith"),
            
            # Test with skip terms
            ("Report_Card.pdf", None),
            ("Assessment_Results.pdf", None),
            
            # Edge cases
            ("", None),
            (None, None),
        ]
        
        for filename, expected_output in test_cases:
            with self.subTest(filename=filename):
                self.assertEqual(extract_student_name_from_filename(filename), expected_output)

if __name__ == "__main__":
    unittest.main()