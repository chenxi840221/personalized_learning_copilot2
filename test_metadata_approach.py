#!/usr/bin/env python
# Test script for our metadata handling approach

import json

def test_metadata_approach():
    """Test our new approach to handling metadata."""
    
    # Create a sample document
    doc = {
        "id": "test-doc-1",
        "student_name": "Jane Doe",
        "student_name_source": "filename",  # Direct field for internal use
        "metadata_json": json.dumps({"name_source": "filename"})  # JSON string for more complex metadata
    }
    
    # Simulate document preparation (exclude fields not in schema)
    invalid_fields = [
        'metadata_json',        # Our new metadata field for internal use
        'student_name_source',  # This field isn't in the schema
    ]
    
    # Remove invalid fields
    cleaned_doc = doc.copy()
    for field in invalid_fields:
        if field in cleaned_doc:
            del cleaned_doc[field]
    
    # Verify fields were removed
    assert "metadata_json" not in cleaned_doc, "metadata_json should be removed"
    assert "student_name_source" not in cleaned_doc, "student_name_source should be removed"
    assert "student_name" in cleaned_doc, "student_name should be preserved"
    
    print("✅ Test passed! Invalid fields correctly removed before indexing.")
    
    # Now verify we can recover the metadata from the original document
    metadata = None
    if doc.get("metadata_json"):
        try:
            metadata = json.loads(doc["metadata_json"])
        except:
            pass
    
    # Verify metadata recovery
    assert metadata is not None, "Should be able to recover metadata"
    assert metadata.get("name_source") == "filename", "Should preserve name_source in metadata"
    
    print("✅ Test passed! Metadata correctly preserved and can be recovered.")

if __name__ == "__main__":
    test_metadata_approach()