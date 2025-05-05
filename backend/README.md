# OpenAI Azure Integration Update

## Overview of Changes

This update standardizes the OpenAI integration in the Personalized Learning Co-pilot by:

1. Using the standard `openai==0.28.0` package with Azure configuration instead of the `azure-openai` package
2. Creating a consistent adapter pattern for OpenAI API calls
3. Fixing async test issues by properly handling coroutines in test cases
4. Ensuring the ABC Education Scraper correctly exports the `run_scraper` function

## Key Components Updated

### 1. OpenAI Adapter

Created a standardized OpenAI adapter (`rag/openai_adapter.py`) that:
- Configures the standard OpenAI package with Azure settings
- Provides consistent async methods for chat completions and embeddings
- Implements a singleton pattern for efficient resource usage

### 2. Test Runner for Async Code

Updated the test runner to properly handle async tests by:
- Creating an `AsyncioTestCase` class that extends `unittest.TestCase`
- Adding a `run_async` helper method to run coroutines in tests
- Ensuring all async test methods are properly awaited

### 3. ABC Education Scraper

Fixed the ABC Education Scraper to:
- Properly export the `run_scraper` function
- Use the standard OpenAI package for embeddings
- Maintain compatibility with the existing test suite

### 4. Test Cases

Updated all test cases to:
- Use the AsyncioTestCase base class for async tests
- Properly mock OpenAI API calls
- Use the run_async helper for coroutine testing

## How to Use

The updated code maintains the same API and functionality but with more consistent error handling and test coverage. No changes are needed in your usage patterns.

Example using the OpenAI adapter:

```python
from rag.openai_adapter import get_openai_adapter

async def generate_completion(prompt):
    # Get the singleton instance
    openai_adapter = await get_openai_adapter()
    
    # Generate a completion
    response = await openai_adapter.create_chat_completion(
        model="your-azure-deployment-name",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response["choices"][0]["message"]["content"]
```

## Testing

Run the updated tests using the test runner:

```bash
cd backend/tests
python run_tests.py
```

For specific test files:

```bash
python run_tests.py --pattern test_openai_adapter.py
```