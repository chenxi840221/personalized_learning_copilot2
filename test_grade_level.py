#!/usr/bin/env python
# Test script for grade level handling

import re

def parse_grade_level(grade_level):
    """
    Parse grade level using the same logic we implemented in the application.
    """
    if grade_level is None:
        # Default to 0 if None
        return 0
        
    if isinstance(grade_level, (int, float)):
        # Already a number, just convert to int
        return int(grade_level)
        
    if isinstance(grade_level, str):
        # First, check for specific keywords like "Preschool", "Kindergarten", etc.
        grade_text = grade_level.lower()
        if any(keyword in grade_text for keyword in ["preschool", "pre-school", "pre school", "nursery"]):
            # Preschool is level 0
            return 0
        elif any(keyword in grade_text for keyword in ["kindergarten", "kinder", "k-"]):
            # Kindergarten is level 0
            return 0
        else:
            # Extract numbers from grade level if it contains text
            numbers = re.findall(r'\d+', grade_level)
            if numbers:
                return int(numbers[0])
            else:
                # Default to 0 if no number found and it's not a recognized keyword
                return 0
    
    # Unknown type, default to 0
    return 0

# Test various grade level values
test_values = [
    None,                 # None value
    0,                    # Already 0
    5,                    # Already a number
    "5",                  # String digit
    "Grade 3",            # Text with number
    "Year 7",             # Text with number
    "Preschool",          # Preschool should be 0
    "Pre-School Class",   # Preschool variation 
    "Kindergarten",       # Kindergarten should be 0
    "K-12",               # Starts with K
    "Foundation Year",    # Text without number
    "Too young for school" # Random text
]

print("Testing grade level parsing logic:")
print("===================================")

for value in test_values:
    result = parse_grade_level(value)
    print(f"Input: {repr(value):<20} Output: {result}")

print("\nAll tests completed!")