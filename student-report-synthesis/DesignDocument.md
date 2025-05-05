# Student Report Synthesis - Design Document

## 1. Introduction

### 1.1 Purpose
This document outlines the detailed technical design of the Student Report Synthesis system, an AI-powered solution for generating personalized student academic reports that align with Australian educational standards. The system is designed to automate the time-consuming process of writing individual student reports while maintaining high quality, personalized feedback tailored to each student's performance.

### 1.2 Scope
The Student Report Synthesis system generates academic reports for primary school students following various Australian state and territory curriculum formats. It leverages Azure OpenAI's GPT-4o for content generation and optionally DALL-E for image generation. The system can produce both individual reports and batch process multiple reports at once in both HTML and PDF formats.

### 1.3 System Overview
The system consists of a modular architecture that separates concerns between content generation, data handling, template rendering, and output formatting. It uses a configurable approach to support multiple reporting formats and styles.

## 2. Architecture Overview

### 2.1 High-Level Architecture
The Student Report Synthesis system follows a modular architecture pattern with clear separation of concerns:

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│                  │      │                  │      │                  │
│   Data Sources   │─────▶│   Core Engine    │─────▶│  Output Formats  │
│                  │      │                  │      │                  │
└──────────────────┘      └──────────────────┘      └──────────────────┘
        │                          │                         │
        ▼                          ▼                         ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Synthetic Data  │      │  AI Integration  │      │       HTML       │
│  Student Profiles│      │     GPT-4o       │      │       PDF        │
│  School Data     │      │     DALL-E       │      │                  │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

### 2.2 Key Components
The system is divided into the following key components:

1. **Report Engine**: The central component coordinating report generation
2. **Style Handler**: Manages different report styles and formats based on educational jurisdictions
3. **AI Content Generator**: Interfaces with Azure OpenAI to generate personalized comments
4. **DALL-E Image Generator**: Optional component for generating school logos and student photos
5. **Template Handler**: Manages HTML templates and rendering
6. **PDF Converter**: Converts HTML reports to PDF format
7. **Student Data Generator**: Creates synthetic student data for testing or demonstration
8. **CLI Interface**: Command-line interface for system interaction

### 2.3 Data Flow
The main data flow through the system:

1. User provides report generation parameters (style, format, etc.)
2. System generates or receives student data
3. AI generates personalized comments for each subject and a general comment
4. (Optional) DALL-E generates school logo and student photo
5. Template renderer creates HTML report using appropriate template
6. PDF converter transforms HTML to PDF if required
7. Final report is saved to the output directory

## 3. Component Design

### 3.1 Report Engine (`enhanced_report_generator.py`)

#### 3.1.1 Responsibilities
- Coordinate the report generation process
- Integrate all system components
- Handle error conditions and fallbacks
- Manage batch processing
- Control image generation

#### 3.1.2 Key Classes and Methods
- `EnhancedReportGenerator`: Main class for report generation
  - `generate_report()`: Generate a single report
  - `generate_batch_reports()`: Generate multiple reports
  - `create_zip_archive()`: Create ZIP archive of batch reports

#### 3.1.3 Design Considerations
- Uses dependency injection for flexibility
- Implements fallback mechanisms for each component
- Provides multiple PDF generation options
- Handles resource cleanup and temporary files

### 3.2 Style Handler (`report_styles.py`)

#### 3.2.1 Responsibilities
- Load and parse style configurations from JSON
- Provide access to style-specific settings
- Support multiple Australian educational standards

#### 3.2.2 Key Classes and Methods
- `ReportStyle`: Enumeration of supported styles
- `ReportStyleHandler`: Manages style configurations
  - `get_style()`: Get style configuration by name
  - `get_available_styles()`: List available styles
  - `get_subjects()`: Get subjects for a style
  - `get_achievement_scale()`: Get achievement scale for a style
  - `get_effort_scale()`: Get effort scale for a style

#### 3.2.3 Design Considerations
- Uses JSON for easy configuration
- Implements singleton pattern for global access
- Creates default styles if none exist

### 3.3 AI Content Generator (`ai_content_generator.py`)

#### 3.3.1 Responsibilities
- Interface with Azure OpenAI's GPT-4o
- Generate personalized subject comments
- Generate holistic general comments
- Handle retry logic and error conditions

#### 3.3.2 Key Classes and Methods
- `AIContentGenerator`: Main class for AI integration
  - `generate_subject_comment()`: Generate comment for a specific subject
  - `generate_general_comment()`: Generate overall comment for the student

#### 3.3.3 Design Considerations
- Uses prompt engineering for educational context
- Manages token limits and retries
- Provides fallback content when AI fails
- Configurable comment length

### 3.4 DALL-E Image Generator (`dalle_image_generator.py`)

#### 3.4.1 Responsibilities
- Interface with Azure OpenAI's DALL-E
- Generate school badges/logos
- Generate student photos
- Handle fallback image generation

#### 3.4.2 Key Classes and Methods
- `DallEImageGenerator`: Main class for image generation
  - `generate_school_badge()`: Create school logo
  - `generate_student_photo()`: Create student photo
  - `_get_fallback_school_badge()`: Create a fallback badge when API fails
  - `_get_fallback_student_photo()`: Create a fallback photo when API fails

#### 3.4.3 Design Considerations
- Validates image size constraints for DALL-E
- Implements prompt engineering for appropriate images
- Creates PILlow-based fallback images when needed
- Returns base64-encoded images for direct template embedding

### 3.5 Template Handler (`template_handler.py`)

#### 3.5.1 Responsibilities
- Load and render HTML templates
- Provide utilities for template customization
- Convert base64 images for embedding
- Create default templates when needed

#### 3.5.2 Key Classes and Methods
- `TemplateHandler`: Main class for template processing
  - `render_template()`: Render HTML template with data
  - `get_image_base64()`: Convert image to base64 data URI
  - `create_default_template()`: Create fallback template
  - `html_to_pdf()`: Basic HTML to PDF conversion

#### 3.5.3 Design Considerations
- Uses Jinja2 for template rendering
- Provides image embedding helpers
- Creates default templates when missing
- Organizes templates by educational jurisdiction

### 3.6 PDF Converter (`pdf_utils.py`)

#### 3.6.1 Responsibilities
- Convert HTML reports to PDF
- Support multiple conversion methods
- Enhance PDF styling and formatting
- Handle conversion errors

#### 3.6.2 Key Classes and Methods
- `convert_html_to_pdf()`: Main conversion function
- `convert_html_to_pdf_with_weasyprint()`: WeasyPrint converter
- `convert_html_to_pdf_with_xhtml2pdf()`: xhtml2pdf converter
- `convert_html_to_pdf_with_wkhtmltopdf()`: wkhtmltopdf converter

#### 3.6.3 Design Considerations
- Implements multiple conversion methods with fallbacks
- Enhances CSS for PDF rendering
- Orders methods by conversion quality
- Handles platform-specific differences

### 3.7 Student Data Generator (`student_data_generator.py`)

#### 3.7.1 Responsibilities
- Generate synthetic student profiles
- Create realistic school information
- Support Australian educational context
- Provide demographic diversity

#### 3.7.2 Key Classes and Methods
- `StudentProfile`: Student data model
- `SchoolProfile`: School data model
- `StudentDataGenerator`: Generator class
  - `generate_student_profile()`: Create student data
  - `generate_school_profile()`: Create school data
  - `generate_classroom()`: Create a set of students

#### 3.7.3 Design Considerations
- Generates culturally diverse synthetic data
- Matches data to Australian educational standards
- Creates realistic student characteristics
- Supports different age groups and grade levels

### 3.8 CLI Interface (`generate_reports.py`, `generate_dalle_reports.py`)

#### 3.8.1 Responsibilities
- Provide command-line interface
- Process user arguments
- Execute report generation commands
- Provide system validation

#### 3.8.2 Key Classes and Methods
- Command-line argument parsing
- Subcommand handlers for different operations
- Validation functions
- Output formatting

#### 3.8.3 Design Considerations
- Uses argparse for structured command handling
- Implements subcommands for different operations
- Provides help and documentation
- Handles environment variables

## 4. Data Models

### 4.1 Student Data Model
```python
{
  "name": {
    "first_name": "...",
    "last_name": "...",
    "full_name": "..."
  },
  "gender": "male/female/non-binary",
  "grade": "Year 3",
  "class": "3A",
  "teacher": {
    "title": "Mr.",
    "last_name": "Smith",
    "full_name": "Mr. Smith"
  },
  "guardians": [
    {
      "first_name": "...",
      "last_name": "...",
      "full_name": "...",
      "gender": "male/female",
      "relationship": "Father/Mother/Guardian"
    }
  ],
  "birth_date": "YYYY-MM-DD",
  "attendance": {
    "total_days": 50,
    "present_days": 45,
    "absent_days": 5,
    "late_days": 2,
    "attendance_rate": 90.0
  },
  "learning_profile": {
    "strengths": ["visual learning", "problem-solving", ...],
    "challenges": ["staying focused", ...],
    "interests": ["art", "science", ...],
    "social_strengths": ["empathy", "collaboration", ...],
    "learning_goals": [...]
  },
  "photo_data": "data:image/png;base64,..."
}
```

### 4.2 School Data Model
```python
{
  "name": "Example Primary School",
  "type": "Primary School",
  "state": "act",
  "suburb": "Canberra",
  "principal": "Dr. Jane Doe",
  "established": 1985,
  "values": ["Respect", "Excellence", "Integrity", ...],
  "motto": "Learning for Life",
  "logo_data": "data:image/png;base64,..."
}
```

### 4.3 Subject Assessment Model
```python
{
  "subject": "Mathematics",
  "achievement": {
    "code": "B",
    "label": "High",
    "description": "High achievement of the standard"
  },
  "effort": {
    "code": "H",
    "label": "High",
    "description": "Consistently demonstrates high effort"
  },
  "comment": "Student has demonstrated excellent problem-solving skills..."
}
```

### 4.4 Report Style Model
```python
{
  "name": "ACT Student Report",
  "description": "Australian Capital Territory school report format",
  "subjects": [...],
  "achievement_scale": [
    {
      "code": "O",
      "label": "Outstanding",
      "description": "..."
    },
    ...
  ],
  "effort_scale": [...],
  "capabilities": {
    "social": [...],
    "self": [...]
  },
  "template_file": "act_template.html",
  "logo_file": "act_logo.png"
}
```

## 5. External Interfaces

### 5.1 Azure OpenAI API
- Used for generating personalized comments
- Requires API key and endpoint configuration
- Uses GPT-4o model for high-quality educational content

#### 5.1.1 Integration Points
- `AIContentGenerator` class interfaces with API
- Uses chat completion API with educational system prompts
- Manages retry logic and error handling

### 5.2 Azure DALL-E API
- Used for generating school logos and student photos
- Requires API key and endpoint configuration
- Uses DALL-E 3 model for image generation

#### 5.2.1 Integration Points
- `DallEImageGenerator` class interfaces with API
- Uses direct API calls with educational prompts
- Manages image formats and sizing

### 5.3 Template Rendering (Jinja2)
- Used for rendering HTML templates
- Processes template variables and structures
- Supports template inheritance and includes

#### 5.3.1 Integration Points
- `TemplateHandler` class interfaces with Jinja2
- Loads templates from templates directory
- Provides helper functions for template rendering

### 5.4 PDF Conversion Libraries
- Multiple libraries used for HTML to PDF conversion
- WeasyPrint (primary), xhtml2pdf (secondary), wkhtmltopdf (tertiary)
- Each provides different capabilities and fallbacks

#### 5.4.1 Integration Points
- `pdf_utils.py` contains conversion functions
- Implements ordered fallback mechanism
- Enhances CSS for better PDF rendering

## 6. Design Patterns and Principles

### 6.1 Singleton Pattern
- Used for `ReportStyleHandler` to provide global access
- Ensures consistent style configurations across the system
- Lazy initialization to load styles when needed

### 6.2 Factory Pattern
- Used for creating reports of different styles
- Centralizes creation logic in the report generator
- Simplifies client code interaction

### 6.3 Strategy Pattern
- Used for PDF conversion methods
- Allows different conversion strategies to be selected
- Enables fallback mechanism when preferred method fails

### 6.4 Dependency Injection
- Used throughout the system to inject dependencies
- Makes components testable and loosely coupled
- Simplifies mocking for unit tests

### 6.5 SOLID Principles
- **Single Responsibility**: Each class has one primary responsibility
- **Open/Closed**: New styles can be added without modifying existing code
- **Liskov Substitution**: Different report generators follow the same interface
- **Interface Segregation**: Clean interfaces for each component
- **Dependency Inversion**: High-level modules depend on abstractions

## 7. Error Handling and Reliability

### 7.1 Error Handling Strategy
- Comprehensive try/except blocks with specific exception handling
- Detailed logging with context information
- Fallback mechanisms for each component
- User-friendly error messages

### 7.2 Fallback Mechanisms
- Multiple PDF conversion methods
- Default templates when custom templates are missing
- Generated placeholder images when DALL-E fails
- Default AI-generated text when OpenAI fails

### 7.3 Logging and Monitoring
- Structured logging throughout the system
- Different log levels for different severity
- File and console output options
- Timestamp and context information

## 8. Performance Considerations

### 8.1 Batch Processing
- Optimized for generating multiple reports in batch
- ZIP archiving for batch downloads
- Progress tracking for long-running batches

### 8.2 Resource Management
- Cleanup of temporary files
- Proper closing of file handles
- Memory management for large batch operations

### 8.3 Asynchronous Operations
- Future expansion plans for asynchronous processing
- Background task processing for large batches
- Progress notifications

## 9. Security Considerations

### 9.1 API Key Management
- Environment variables for sensitive credentials
- .env file support with .env.example template
- No hardcoded secrets in the codebase

### 9.2 Input Validation
- Validation of user inputs
- Sanitization of data used in templates
- Prevention of template injection

### 9.3 Output Safety
- Safe handling of generated content
- Content filtering for appropriate educational context
- Image generation safety measures

## 10. Testing Strategy

### 10.1 Unit Testing
- Test each component in isolation
- Mock external dependencies
- Focus on edge cases and error conditions

### 10.2 Integration Testing
- Test component interactions
- Verify end-to-end report generation
- Validate different report styles

### 10.3 System Testing
- Test the complete system
- Verify output formats and quality
- Batch processing tests

## 11. Deployment and Operations

### 11.1 Installation
- Python package installation
- Virtual environment setup
- Dependency management

### 11.2 Configuration
- Environment variable configuration
- Template customization
- Style configuration

### 11.3 Monitoring and Maintenance
- Logging configuration
- Error monitoring
- Performance tracking

## 12. Future Enhancements

### 12.1 Planned Features
- Web interface for report generation
- Student data import from CSV/Excel
- Integration with school management systems
- More Australian state/territory report formats
- Email delivery of generated reports

### 12.2 Technical Improvements
- Asynchronous processing for batch operations
- In-memory caching for frequently used data
- Performance optimizations for large batch processing
- Additional PDF styling options

## 13. Appendices

### 13.1 Glossary
- **ACT**: Australian Capital Territory
- **NSW**: New South Wales
- **QLD**: Queensland
- **VIC**: Victoria
- **GPT-4o**: OpenAI's latest language model
- **DALL-E**: OpenAI's image generation model

### 13.2 References
- Australian Curriculum Framework
- State/Territory Reporting Standards
- Azure OpenAI API Documentation
- Jinja2 Template Documentation
- WeasyPrint Documentation