# DALL-E Integration for Student Reports

This project includes integration with Azure OpenAI's DALL-E model to generate custom images for student reports:

1. **School Badges/Logos**: Customized school emblems based on school name, type, and colors
2. **Student Photos**: Realistic student portraits for use in reports

## Usage

### Basic Usage

Use the `--images` flag when generating reports:

```bash
python generate_reports.py single --style act --format pdf --images
```

### Dedicated Script

For more control, use the dedicated DALL-E reports script:

```bash
python generate_dalle_reports.py single --style act --badge-style modern --image-size 512x512
```

## Configuration Options

- **Badge Style**: modern, traditional, minimalist, elegant
- **Badge Colors**: Comma-separated color names (e.g., "navy blue,gold")
- **Photo Style**: school portrait, yearbook, classroom, etc.
- **Image Size**: 1024x1024 (high quality) or 512x512 (faster generation)

## Requirements

- Azure OpenAI API access with DALL-E model capabilities
- OPENAI_ENDPOINT and OPENAI_KEY environment variables configured

## Technical Details

The DALL-E integration is managed by the `DallEImageGenerator` class in `src/report_engine/ai/dalle_image_generator.py`.
