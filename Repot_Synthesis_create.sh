#!/bin/bash
# create_file_structure.sh
# Script to create the directory and file structure for the Student Report Synthesis System

# Exit on error
set -e

echo "Creating file structure for Student Report Synthesis System..."

# Create main project directory
mkdir -p student-report-synthesis
cd student-report-synthesis

# Create subdirectories
mkdir -p templates
mkdir -p output
mkdir -p uploads
mkdir -p static
mkdir -p logs

# Create empty files
touch README.md
touch .env.example
touch requirements.txt
touch Dockerfile
touch deployment.sh
touch azure-setup.sh

# Make shell scripts executable
chmod +x deployment.sh
chmod +x azure-setup.sh

# Create main application file
cat > main.py << 'EOF'
import os
import json
import uuid
import shutil
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from tempfile import NamedTemporaryFile

from student_report_system import StudentReportSystem

# Initialize FastAPI app
app = FastAPI(
    title="Student Report Synthesis System",
    description="API for generating synthetic student reports based on templates",
    version="1.0.0"
)

# App configuration code will go here

if __name__ == "__main__":
    import uvicorn
    print("Starting Student Report Synthesis System...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# Create student report system core file
cat > student_report_system.py << 'EOF'
import os
import json
import uuid
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# Placeholder for the StudentReportSystem class
class StudentReportSystem:
    def __init__(self, form_recognizer_endpoint, form_recognizer_key, 
                 openai_endpoint, openai_key, openai_deployment):
        """Initialize the student report system with Azure service credentials."""
        # Implementation code will go here
        pass
    
    def extract_template_structure(self, template_path, template_name):
        """Extract structure from a report template using Azure Document Intelligence."""
        # Implementation code will go here
        pass
    
    # Other methods will go here

# Example usage
if __name__ == "__main__":
    # This would be for local testing only
    pass
EOF

# Create basic HTML template
cat > static/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Report Synthesis System</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/alpinejs/3.10.5/cdn.min.js" defer></script>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold text-center text-blue-800">Student Report Synthesis System</h1>
        <p class="text-center text-gray-600">Generate standardized student reports following Australian education guidelines</p>
        
        <!-- Content will go here -->
        
    </div>
</body>
</html>
EOF

# Create requirements.txt with necessary packages
cat > requirements.txt << 'EOF'
fastapi==0.95.1
uvicorn==0.22.0
python-multipart==0.0.6
azure-ai-formrecognizer==3.2.1
azure-ai-documentintelligence==1.0.0
openai==1.3.5
reportlab==3.6.12
pillow==9.5.0
pandas==2.0.1
python-jose==3.3.0
passlib==1.7.4
pydantic==1.10.8
jinja2==3.1.2
aiofiles==23.1.0
EOF

# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p templates output uploads static

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Create deployment script
cat > deployment.sh << 'EOF'
#!/bin/bash

# Set environment variables (replace with your actual Azure service credentials)
export FORM_RECOGNIZER_ENDPOINT="https://your-form-recognizer.cognitiveservices.azure.com/"
export FORM_RECOGNIZER_KEY="your-form-recognizer-key"
export OPENAI_ENDPOINT="https://your-openai.openai.azure.com/"
export OPENAI_KEY="your-openai-key"
export OPENAI_DEPLOYMENT="gpt-4o"

# Build Docker image
docker build -t student-report-system .

# Run Docker container
docker run -d \
  --name student-report-system \
  -p 8000:8000 \
  -e FORM_RECOGNIZER_ENDPOINT=${FORM_RECOGNIZER_ENDPOINT} \
  -e FORM_RECOGNIZER_KEY=${FORM_RECOGNIZER_KEY} \
  -e OPENAI_ENDPOINT=${OPENAI_ENDPOINT} \
  -e OPENAI_KEY=${OPENAI_KEY} \
  -e OPENAI_DEPLOYMENT=${OPENAI_DEPLOYMENT} \
  -v $(pwd)/templates:/app/templates \
  -v $(pwd)/output:/app/output \
  student-report-system

echo "Student Report Synthesis System is now running at http://localhost:8000"
echo "Access the web interface by opening this URL in your browser"
EOF

# Create a sample .env.example file
cat > .env.example << 'EOF'
FORM_RECOGNIZER_ENDPOINT=https://your-form-recognizer.cognitiveservices.azure.com/
FORM_RECOGNIZER_KEY=your-form-recognizer-key
OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
OPENAI_KEY=your-openai-key
OPENAI_DEPLOYMENT=gpt-4o
EOF

# Create a basic README
cat > README.md << 'EOF'
# Student Report Synthesis System

A proof-of-concept project for generating standardized primary student reports following Australian education guidelines. This system uses Azure's AI services to extract information from report templates and produce high-quality, standards-compliant student reports.

## Setup Instructions

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables by copying `.env.example` to `.env` and filling in your Azure credentials.

3. Run the application:
   ```bash
   python main.py
   ```

## Docker Deployment

```bash
./deployment.sh
```

Visit http://localhost:8000 to access the web interface.
EOF

echo "File structure created successfully in the student-report-synthesis directory!"
echo "Navigate to the directory and explore the files:"
echo "cd student-report-synthesis"