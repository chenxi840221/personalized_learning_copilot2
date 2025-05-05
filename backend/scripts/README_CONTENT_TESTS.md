# Azure AI Search Content Testing Scripts

This directory contains scripts for testing and analyzing the content in the Azure AI Search `educational-content` index.

## Prerequisites

- Azure AI Search credentials properly configured in your environment
- Python 3.7+
- The following packages installed:
  - `tabulate` (for table output formatting)
  - All backend dependencies from `requirements.txt`

## Scripts Overview

### 1. `test_content_index.py`

This script retrieves and displays detailed statistics about the content in the Azure AI Search index.

**Usage:**
```bash
python scripts/test_content_index.py [--subject SUBJECT] [--count COUNT] [--show-samples]
```

**Options:**
- `--subject SUBJECT`: Filter by subject (e.g., "Maths", "Science")
- `--count COUNT`: Number of items to analyze (default: 100)
- `--show-samples`: Display sample content items

**Example:**
```bash
# Show statistics for Math content with samples
python scripts/test_content_index.py --subject "Maths" --show-samples

# Analyze 500 items across all subjects
python scripts/test_content_index.py --count 500
```

### 2. `test_content_retrieval.py`

This script tests the retrieval capabilities for all content without subject filters, simulating the behavior of the recommendations endpoint and verifying how many items can be displayed at once.

**Usage:**
```bash
python scripts/test_content_retrieval.py
```

The script performs three tests:
1. **Recommendations Endpoint Simulation**: Tests the logic used in the API to retrieve items across all subjects
2. **Direct Content Retrieval**: Attempts to retrieve all content without filters in a single request
3. **Pagination Test**: Retrieves content using pagination to verify how many total items can be accessed

## Sample Output

The scripts produce detailed output with statistics about the content in the index, including:

- Total number of items
- Distribution by subject, content type, difficulty level, and grade level
- Retrieval times
- Verification of uniqueness (detecting any duplicate items)

## Troubleshooting

If you encounter errors while running the scripts:

1. Ensure Azure AI Search credentials are properly set in environment variables
2. Make sure you're running the scripts from the backend directory:
   ```bash
   cd backend
   python scripts/test_content_index.py
   ```
3. Check that all required packages are installed:
   ```bash
   pip install -r requirements.txt
   pip install tabulate
   ```