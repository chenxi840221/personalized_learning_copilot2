# Student Report Synthesis

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)

An AI-powered system for generating personalized student reports following Australian educational standards with support for different state/territory formats (ACT, NSW, QLD, VIC, etc.).

## 📋 Overview

This system automates the creation of student academic reports by leveraging Azure OpenAI's GPT-4o to generate realistic, personalized report comments. It supports multiple Australian educational standards and formats, allowing schools to produce consistent and professional reports across different states and territories.

### 🎯 Key Features

- **🤖 AI-Generated Content**: Uses Azure OpenAI's GPT-4o to generate realistic, personalized report comments based on student achievement and effort levels
- **🏫 Multiple Report Styles**: Supports different Australian educational standards (ACT, NSW, QLD, VIC, etc.)
- **👨‍🎓 Synthetic Student Profiles**: Generates diverse, realistic student profiles for testing
- **📊 Customizable Assessments**: Creates comments tailored to specific subjects and student profiles
- **⚡ Batch Processing**: Generate multiple reports simultaneously with unique student profiles
- **📄 Multiple Output Formats**: Export reports as PDF or HTML with professionally formatted layouts
- **🖼️ DALL-E Image Generation**: Integrated DALL-E capabilities for generating school logos and student photos
- **🔄 Flexible Template System**: Easily customize report templates with Jinja2 templating
- **📐 Multiple Image Sizes**: Support for various DALL-E image sizes (1024x1024, 1792x1024, 1024x1792)

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- Azure OpenAI API access
- Required Python packages (see requirements.txt)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/student-report-synthesis.git
   cd student-report-synthesis
   ```

2. **Set up a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Create a `.env` file in the project root
   - Add your Azure OpenAI credentials:
     ```
     OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
     OPENAI_KEY=your-openai-key
     OPENAI_DEPLOYMENT=gpt-4o
     ```

5. **Set up project directories**
   ```bash
   python manage_project.py setup
   ```

### Optional Dependencies

For enhanced PDF generation:
- **WeasyPrint** (recommended for best quality)
  ```bash
  pip install weasyprint
  ```
- **xhtml2pdf** (fallback option)
  ```bash
  pip install xhtml2pdf
  ```
- **wkhtmltopdf** (external tool for improved rendering)
  - Download from: https://wkhtmltopdf.org/downloads.html
- **ReportLab** (additional PDF generation capabilities)
  ```bash
  pip install reportlab
  ```

## 🚀 Usage

### Quick Start

Generate a sample report with default settings:
```bash
python main.py
```

### Command-line Interface

The system provides a comprehensive command-line interface for report generation:

#### Generate a single report

```bash
python generate_reports.py single --style act --format pdf --comment-length standard
```

#### Generate multiple reports in batch

```bash
python generate_reports.py batch --num 10 --style nsw --format pdf
```

#### List available report styles

```bash
python generate_reports.py styles
```

#### Validate your setup

```bash
python generate_reports.py validate
```

### Command Options

- `--style`: Report style (generic, act, nsw, qld, vic, etc.)
- `--format`: Output format (pdf, html)
- `--comment-length`: Length of generated comments (brief, standard, detailed)
- `--output`: Custom output file path (for single reports)
- `--num`: Number of reports to generate (for batch mode)
- `--batch-id`: Custom batch ID (for batch mode)
- `--images`: Enable DALL-E image generation (requires Azure OpenAI DALL-E access)

### DALL-E Image Integration

For reports with AI-generated images:

```bash
python generate_dalle_reports.py single --style act --badge-style modern
```

#### DALL-E Configuration Options

- `--badge-style`: Style of school badge/logo (modern, traditional, minimalist, elegant)
- `--badge-colors`: Comma-separated color names (e.g., "navy blue,gold")
- `--photo-style`: Style for student photos (school portrait, yearbook, classroom)
- `--image-size`: Size for generated images (1024x1024, 1792x1024, 1024x1792)

## 🏫 Supported Report Styles

The system supports multiple Australian educational jurisdiction styles:

| Style | Description |
|-------|-------------|
| generic | Standard report format with basic subjects |
| act | Australian Capital Territory format |
| nsw | New South Wales format |
| qld | Queensland format |
| vic | Victoria format |

Each style includes:
- Jurisdiction-specific subject names
- Custom achievement and effort scales
- Specialized report layouts and terminology

## 📁 Project Structure

```
student-report-synthesis/
├── src/
│   └── report_engine/
│       ├── ai/                 # AI content generation
│       │   ├── ai_content_generator.py  # GPT-4o integration
│       │   └── dalle_image_generator.py # DALL-E integration
│       ├── styles/             # Report style handling
│       ├── templates/          # HTML template handling
│       ├── utils/              # Utility functions
│       │   └── pdf_utils.py    # PDF conversion utilities
│       ├── student_data_generator.py  # Synthetic profiles
│       └── enhanced_report_generator.py  # Main generator
├── report_styles/              # Style configurations (JSON)
├── templates/                  # HTML templates
├── static/                     # Static assets
│   ├── css/                    # CSS stylesheets
│   └── images/
│       └── logos/              # School and jurisdiction logos
├── output/                     # Generated reports
├── main.py                     # Main entry point
├── generate_reports.py         # CLI for report generation
├── generate_dalle_reports.py   # DALL-E integration script
└── manage_project.py           # Project setup utility
```

## ✨ Customization

### Templates

Report templates are HTML files located in the `templates/` directory. They can be customized to match your school's branding and layout preferences.

```bash
# Example: Create a new template for Queensland reports
cp templates/nsw_template.html templates/qld_template.html
# Edit qld_template.html with your preferred changes
```

### Report Styles

Each report style is defined in a JSON file in the `report_styles/` directory. You can customize:

- Subject names
- Achievement scales
- Effort scales
- Additional assessment criteria

### AI Prompts

The AI prompts used to generate report comments can be found in `src/report_engine/ai/ai_content_generator.py`. You can adjust these to match your school's tone and content requirements.

## 💻 Development

### Adding a New Report Style

1. Create a new JSON file in `report_styles/` (e.g., `sa.json` for South Australia)
2. Define the style properties (subjects, achievement scale, effort scale, etc.)
3. Optionally create a corresponding HTML template in `templates/` (e.g., `sa_template.html`)

Example JSON configuration:
```json
{
  "name": "South Australia Student Report",
  "description": "South Australia school report format",
  "subjects": ["English", "Mathematics", "Science", "HASS", ...],
  "achievement_scale": [
    {"code": "A", "label": "Excellent", "description": "..."},
    ...
  ],
  "effort_scale": [
    {"code": "E", "label": "Excellent", "description": "..."},
    ...
  ],
  "template_file": "sa_template.html"
}
```

### Creating Custom Templates

Templates use Jinja2 syntax and have access to the following data structure:

```python
{
  "student": {
    "name": {"first_name": "...", "last_name": "...", "full_name": "..."},
    "gender": "male/female/non-binary",
    "grade": "Year 3",
    "class": "3A",
    "teacher": {"title": "Mr.", "last_name": "Smith", "full_name": "Mr. Smith"}
  },
  "school": {
    "name": "Example Primary School",
    "type": "Primary School",
    "state": "act",
    "suburb": "Canberra",
    "principal": "Dr. Jane Doe"
  },
  "subjects": [
    {
      "subject": "English",
      "achievement": {"code": "B", "label": "High"},
      "effort": {"code": "E", "label": "Excellent"},
      "comment": "..."
    },
    ...
  ],
  "general_comment": "...",
  "attendance": {
    "present_days": 45,
    "absent_days": 5,
    "late_days": 2,
    "attendance_rate": 90.0
  },
  "semester": "1",
  "year": 2025,
  "report_date": "19 April 2025",
  "images": {  # When DALL-E is enabled
    "school_logo": "path/to/generated/logo.png",
    "student_photo": "path/to/generated/photo.png"
  }
}
```

## 🧪 Testing

Run the test suite:

```bash
pytest
```

For coverage analysis:

```bash
pytest --cov=src tests/
```

## 📝 License

[MIT License](LICENSE)

## 🙏 Acknowledgements

- This project uses Azure OpenAI services for AI-generated content and DALL-E for image generation
- PDF conversion uses multiple libraries including WeasyPrint, xhtml2pdf, and ReportLab
- Template rendering uses Jinja2