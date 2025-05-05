# Student Report Synthesis
# User Manual

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation Guide](#installation-guide)
3. [Configuration](#configuration)
4. [Basic Usage](#basic-usage)
5. [Report Generation](#report-generation)
6. [Report Styles](#report-styles)
7. [Customization](#customization)
8. [DALL-E Image Generation](#dall-e-image-generation)
9. [Batch Processing](#batch-processing)
10. [Troubleshooting](#troubleshooting)
11. [FAQ](#faq)
12. [Appendices](#appendices)

---

## Introduction

### Overview

Student Report Synthesis is an AI-powered system for generating personalized student academic reports following Australian educational standards. It leverages Azure OpenAI's GPT-4o to create authentic, insightful comments and optionally uses DALL-E to generate school logos and student photos.

### Key Features

- Generate personalized subject and general comments using AI
- Support for multiple Australian educational jurisdictions (ACT, NSW, QLD, VIC, etc.)
- Create realistic synthetic student profiles for testing
- Output reports in both PDF and HTML formats
- Generate school logos and student photos using DALL-E
- Process multiple reports in batch mode
- Customize report templates and styles

### System Requirements

- Python 3.8 or higher
- Azure OpenAI API access with GPT-4o deployment
- Optional: Azure OpenAI API access with DALL-E 3 deployment
- 4GB RAM (minimum), 8GB recommended for batch processing
- 500MB free disk space
- Internet connection for API access

---

## Installation Guide

### Prerequisites

Before installing Student Report Synthesis, ensure you have:

1. Python 3.8 or higher installed on your system
2. Access to Azure OpenAI services with:
   - GPT-4o model deployment
   - Optionally, DALL-E 3 model deployment
3. pip (Python package manager)

### Step-by-Step Installation

1. **Clone or download the repository**

   ```bash
   git clone https://github.com/yourusername/student-report-synthesis.git
   cd student-report-synthesis
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**

   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install required dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Install PDF generation libraries (optional but recommended)**

   For better PDF generation quality:

   ```bash
   pip install weasyprint
   ```

   Alternative PDF generation options:

   ```bash
   pip install xhtml2pdf
   ```

6. **Initialize the project structure**

   ```bash
   python manage_project.py setup
   ```

### Verifying Installation

To verify your installation:

```bash
python generate_reports.py validate
```

This command checks:
- Required directories exist
- Environment variables are set properly
- Style configurations are available
- Template files are present
- Dependencies are installed

If all checks pass, you're ready to use the system!

---

## Configuration

### Environment Variables

Create a `.env` file in the project root directory with your Azure OpenAI credentials:

```
OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
OPENAI_KEY=your-openai-key
OPENAI_DEPLOYMENT=gpt-4o
```

For DALL-E image generation, ensure your Azure OpenAI account has access to DALL-E models.

### Directory Structure

The project uses several directories for operation:

- `templates/`: HTML templates for report styles
- `report_styles/`: JSON configuration files for report styles
- `static/images/logos/`: Logo images for various educational jurisdictions
- `output/`: Generated reports are saved here
- `logs/`: Log files for debugging

### Style Configuration

Report styles are defined in JSON files located in the `report_styles/` directory. The system includes configurations for ACT, NSW, QLD, VIC, and a generic style.

To view available styles:

```bash
python generate_reports.py styles
```

---

## Basic Usage

### Quick Start

Generate a sample report with default settings:

```bash
python main.py
```

This will:
1. Create a synthetic student profile
2. Generate AI comments for each subject
3. Create a general comment
4. Produce a PDF report in the `output/` directory

### Command-Line Interface

The system provides a comprehensive command-line interface through `generate_reports.py`. The basic syntax is:

```bash
python generate_reports.py <command> [options]
```

Available commands:
- `single`: Generate a single report
- `batch`: Generate multiple reports
- `styles`: List available report styles
- `validate`: Validate the system setup

For help with any command:

```bash
python generate_reports.py <command> --help
```

---

## Report Generation

### Generating a Single Report

To generate a single report:

```bash
python generate_reports.py single --style act --format pdf
```

Options:
- `--style`: Report style (act, nsw, qld, vic, generic)
- `--format`: Output format (pdf, html)
- `--comment-length`: Length of comments (brief, standard, detailed)
- `--output`: Specify output file path
- `--images`: Enable DALL-E image generation

Example with all options:

```bash
python generate_reports.py single --style nsw --format pdf --comment-length detailed --output "output/john_smith_report.pdf" --images
```

### Understanding the Output

The system generates:

1. An HTML file with the report content
2. A PDF file (if PDF format is selected)

Reports are named using the pattern:
`{StudentName}_{Style}_{Semester}_{Year}.{format}`

Example: `John_Smith_act_1_2025.pdf`

---

## Report Styles

### Available Styles

The system supports multiple Australian educational jurisdiction styles:

| Style | Description | Key Features |
|-------|-------------|-------------|
| `act` | Australian Capital Territory | 5-point achievement scale (O, H, A, P, L), 4-point effort scale (C, U, S, R) |
| `nsw` | New South Wales | 5-point achievement scale (A-E), 3-point effort scale (H, S, L) |
| `qld` | Queensland | 5-point achievement scale (A-E), 3-point effort scale (H, S, L) |
| `vic` | Victoria | 5-point achievement scale, 5-point effort scale |
| `generic` | Standard format | 5-point achievement scale (A-E), 3-point effort scale (H, S, L) |

### Style-Specific Features

Each style includes:
- Jurisdiction-specific subject names
- Custom achievement and effort scales
- Specialized report layouts
- Style-specific terminology
- Jurisdiction logos (where available)

### Selecting a Style

Specify the style using the `--style` option:

```bash
python generate_reports.py single --style qld
```

---

## Customization

### Template Customization

Report templates are HTML files using Jinja2 syntax, located in the `templates/` directory. You can modify existing templates or create new ones.

To customize a template:

1. Copy an existing template as a starting point:
   ```bash
   cp templates/act_template.html templates/my_custom_template.html
   ```

2. Edit the HTML file with your preferred styling and layout

3. Update the corresponding style JSON file to point to your new template:
   ```json
   {
     "template_file": "my_custom_template.html"
   }
   ```

### Style Customization

To customize a report style:

1. Copy an existing style file:
   ```bash
   cp report_styles/act.json report_styles/my_custom_style.json
   ```

2. Edit the JSON file to customize:
   - Subjects list
   - Achievement scale
   - Effort scale
   - Additional assessment criteria

3. Use your custom style:
   ```bash
   python generate_reports.py single --style my_custom_style
   ```

### Comment Customization

To adjust the AI-generated comments:

1. Use the `--comment-length` option:
   - `brief`: 30-40 words per subject
   - `standard`: 60-80 words per subject (default)
   - `detailed`: 100-150 words per subject

2. For advanced customization, you can modify the prompts in the `AIContentGenerator` class.

---

## DALL-E Image Generation

### Overview

The system can generate school logos and student photos using Azure OpenAI's DALL-E 3 model. This feature requires:

- Azure OpenAI API access with DALL-E 3 model
- The `--images` flag during report generation

### Generating Reports with Images

```bash
python generate_reports.py single --style act --images
```

### Advanced Image Options

For more control over image generation, use the dedicated DALL-E reports script:

```bash
python generate_dalle_reports.py single --style act --badge-style modern --badge-colors "navy blue,gold" --image-size 1024x1024
```

Options:
- `--badge-style`: Style for school logos (modern, traditional, minimalist, elegant)
- `--badge-colors`: Comma-separated colors for the badge
- `--image-size`: Size of generated images (1024x1024, 1792x1024, 1024x1792)

### Available DALL-E Commands

The `generate_dalle_reports.py` script supports:

- `single`: Generate a single report with images
- `batch`: Generate multiple reports with images
- `styles`: View style-specific image settings

---

## Batch Processing

### Generating Multiple Reports

To generate multiple reports at once:

```bash
python generate_reports.py batch --num 10 --style act --format pdf
```

Options:
- `--num`: Number of reports to generate
- `--style`: Report style to use
- `--format`: Output format (pdf, html)
- `--batch-id`: Custom batch ID (generated if not provided)
- `--comment-length`: Length of comments
- `--images`: Enable DALL-E image generation

### Batch Output

Batch processing creates:
1. A directory named with the batch ID (e.g., `batch_a1b2c3d4`)
2. Individual reports within this directory
3. A metadata JSON file with batch information
4. A ZIP archive containing all reports

Example:
```
output/
└── batch_a1b2c3d4/
    ├── report_1.pdf
    ├── report_2.pdf
    ├── ...
    ├── report_10.pdf
    └── metadata.json
└── batch_a1b2c3d4.zip
```

### Batch with DALL-E Images

For batch processing with DALL-E images:

```bash
python generate_dalle_reports.py batch --num 5 --style nsw --format pdf
```

---

## Troubleshooting

### Common Issues

#### Issue: API Authentication Error

**Symptoms**: Error message about invalid API key or endpoint

**Solution**:
1. Check your `.env` file for correct credentials
2. Verify the Azure OpenAI service is active
3. Ensure the deployment name matches your Azure setup

#### Issue: Missing Template Error

**Symptoms**: Error about missing template file

**Solution**:
1. Run the validation command to check template files:
   ```bash
   python generate_reports.py validate
   ```
2. Check if the template exists in the `templates/` directory
3. Create the missing template file

#### Issue: PDF Generation Failure

**Symptoms**: HTML output works but PDF fails to generate

**Solution**:
1. Install additional PDF libraries:
   ```bash
   pip install weasyprint xhtml2pdf
   ```
2. On Windows, ensure you have GTK+ installed for WeasyPrint
3. Try using a different output format:
   ```bash
   python generate_reports.py single --format html
   ```

#### Issue: DALL-E Image Generation Failure

**Symptoms**: Report generates but without images

**Solution**:
1. Verify your Azure OpenAI account has DALL-E model access
2. Check the deployment name for DALL-E in your environment
3. Verify the image size is valid for DALL-E 3 (1024x1024, 1792x1024, or 1024x1792)

### Log Files

Check the log files in the `logs/` directory for detailed error information:
- `app.log`: Main application log
- `report_generator.log`: Report generation log
- `dalle_demo.log`: DALL-E image generation log

---

## FAQ

### General Questions

**Q: How many reports can I generate in a batch?**

A: The system can handle up to 100 reports in a single batch. For larger batches, consider running multiple batch operations.

**Q: How long does it take to generate a report?**

A: A single report typically takes 30-60 seconds, depending on:
- AI response time
- Image generation (if enabled)
- Report complexity and length
- PDF conversion method

**Q: Does the system require internet access?**

A: Yes, the system requires internet access to communicate with Azure OpenAI services for AI-generated content and images.

**Q: Can I use my own student data instead of synthetic data?**

A: Yes, the system accepts custom student data. You would need to structure it according to the expected format (see the Data Structure section in the Appendices).

### Report Content

**Q: How realistic are the AI-generated comments?**

A: The comments are designed to sound like they were written by experienced teachers. The GPT-4o model has been prompted to produce educationally appropriate, constructive, and personalized comments.

**Q: Can I generate reports for high school students?**

A: The system is primarily designed for primary school reports, but can be adapted for high school by customizing the subjects and assessment criteria in the style configuration files.

**Q: Are the student profiles completely random?**

A: The synthetic student profiles use carefully designed algorithms to create realistic, diverse student data with appropriate Australian names, demographics, and educational characteristics.

---

## Appendices

### Data Structure

If providing custom student data, use this structure:

```json
{
  "student": {
    "name": {
      "first_name": "John",
      "last_name": "Smith",
      "full_name": "John Smith"
    },
    "gender": "male",
    "grade": "Year 4",
    "class": "4A",
    "teacher": {
      "title": "Mr.",
      "last_name": "Jones",
      "full_name": "Mr. Jones"
    }
  },
  "school": {
    "name": "Sunshine Primary School",
    "type": "Primary School",
    "state": "act",
    "suburb": "Canberra",
    "principal": "Dr. Sarah Wilson"
  },
  "semester": "1",
  "year": "2025"
}
```

### Command Reference

#### Main Scripts

- `main.py`: Quick sample report generation
- `generate_reports.py`: Complete command-line interface
- `generate_dalle_reports.py`: Reports with DALL-E images
- `manage_project.py`: Project setup and management

#### Report Generation Options

| Option | Description | Values |
|--------|-------------|--------|
| `--style` | Report style | act, nsw, qld, vic, generic, [custom] |
| `--format` | Output format | pdf, html |
| `--comment-length` | Comment detail | brief, standard, detailed |
| `--output` | Output file path | Any valid path |
| `--images` | Enable images | Flag (no value) |
| `--num` | Batch size | Integer number |
| `--batch-id` | Batch identifier | String identifier |

#### DALL-E Image Options

| Option | Description | Values |
|--------|-------------|--------|
| `--badge-style` | School badge style | modern, traditional, minimalist, elegant |
| `--badge-colors` | Badge colors | Comma-separated color names |
| `--image-size` | Image dimensions | 1024x1024, 1792x1024, 1024x1792 |

### Support Resources

For additional help:
- Project documentation: [docs/](docs/)
- Issue tracker: [GitHub Issues](https://github.com/chenxi840221/student-report-synthesis/issues)
- Developer contact: xi.chen3@dxc.com