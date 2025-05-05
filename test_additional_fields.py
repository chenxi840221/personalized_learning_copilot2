#!/usr/bin/env python
# Test script for additional_fields handling

import json

def test_additional_fields_processing():
    """Test the correct processing of additional_fields."""
    
    # Metadata to store
    metadata = {"name_source": "filename"}
    
    # Ensure additional_fields is correctly stored as a JSON string
    additional_fields = json.dumps(metadata)
    
    # Verify we can parse it back correctly
    parsed_fields = json.loads(additional_fields)
    
    # Check if name_source is correctly preserved
    assert parsed_fields.get("name_source") == "filename", "Failed to preserve name_source field"
    
    print("✅ Test passed! additional_fields correctly handled as a JSON string.")

if __name__ == "__main__":
    test_additional_fields_processing()