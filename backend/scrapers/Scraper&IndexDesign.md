# Scraper and Indexing System Design Document

## 1. Overview

This document describes the architectural design and implementation details for the scraping and indexing subsystem of the Personalized Learning Co-pilot. The subsystem is responsible for collecting educational content from the web, processing it, and indexing it for retrieval by the learning recommendation engine.

## 2. Architecture

### 2.1 System Components

The scraper and indexing system consists of the following major components:

1. **Resource Indexer**: Discovers and catalogs educational resources across multiple subjects and age groups.
2. **Content Extractor**: Processes discovered resources to extract useful content and metadata.
3. **Content Analyzer**: Analyzes extracted content to determine educational properties and generate embeddings.
4. **Vector Store Integration**: Indexes processed content in Azure AI Search for efficient retrieval.
5. **LangChain Manager**: Provides a unified interface to LangChain components for content processing and retrieval.

### 2.2 Data Flow

```
[Web Sources] → [Resource Indexer] → [Resource Index] → [Content Extractor] → [Content Analyzer] → [Vector Store] → [Learning Recommendation Engine]
```

### 2.3 Integration Points

- **Azure OpenAI**: Used for generating embeddings and analyzing content
- **Azure AI Search**: Used as the vector store for indexed content
- **LangChain**: Used for document processing and RAG functionality

## 3. Component Details

### 3.1 Resource Indexer (`edu_resource_indexer.py`)

#### Purpose
Discovers educational resources from web sources and builds a comprehensive index of resource metadata.

#### Key Features
- Multi-subject crawling with configurable subject list
- Age group detection and categorization
- Resource link extraction and deduplication
- Pagination handling for exhaustive content discovery
- Configurable rate limiting to respect source websites

#### Implementation Details
- Uses Playwright for browser automation
- Implements retry mechanisms for robust scraping
- Outputs a structured JSON index of all discovered resources
- Handles different website layouts and structures

#### Data Model
```json
{
  "created_at": "ISO timestamp",
  "total_resources": 250,
  "subjects": {
    "Mathematics": {
      "count": 80,
      "age_groups": {
        "Years F-2": {
          "count": 25,
          "resources": [
            {
              "id": "unique-id",
              "title": "Resource Title",
              "url": "https://example.com/resource",
              "subject": "Mathematics",
              "age_group": "Years F-2",
              "discovered_at": "ISO timestamp"
            }
          ]
        }
      }
    }
  }
}
```

### 3.2 Content Extractor (`content_extractor.py`)

#### Purpose
Processes discovered resources to extract detailed content, metadata, and educational properties.

#### Key Features
- Content type detection (article, video, interactive, etc.)
- Transcript extraction for multimedia content
- Difficulty level and grade level detection
- Duration estimation
- Keyword extraction

#### Implementation Details
- Uses Playwright for content extraction
- Implements media-specific extraction strategies
- Handles different content types (text, audio, video, interactive)
- Outputs structured content with metadata

#### Data Model
```json
{
  "id": "unique-id",
  "title": "Content Title",
  "description": "Content description",
  "content_type": "video|article|interactive|quiz|worksheet|lesson|activity",
  "subject": "Subject Name",
  "topics": ["Topic1", "Topic2"],
  "url": "https://example.com/content",
  "source": "ABC Education",
  "difficulty_level": "beginner|intermediate|advanced",
  "grade_level": [5, 6, 7],
  "duration_minutes": 15,
  "keywords": ["keyword1", "keyword2"],
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "metadata": {
    "content_text": "Extracted text content",
    "transcription": "Video/audio transcription",
    "thumbnail_url": "URL to thumbnail"
  }
}
```

### 3.3 Content Analyzer (`content_analyzer.py`)

#### Purpose
Analyzes extracted content to determine educational properties and generate embeddings for semantic search.

#### Key Features
- Content difficulty analysis
- Grade level appropriateness detection
- Learning outcome identification
- Keyword extraction and topic modeling
- Embedding generation for semantic search

#### Implementation Details
- Uses Azure OpenAI for embedding generation
- Implements education-specific content analysis algorithms
- Outputs analyzed content with relevant educational metadata

### 3.4 Vector Store Integration

#### Purpose
Indexes processed content in Azure AI Search for efficient retrieval by the learning recommendation engine.

#### Key Features
- Vector embedding storage and retrieval
- Full-text search capabilities
- Filtering by subject, grade level, content type, etc.
- Hybrid search combining vector similarity and metadata filtering

#### Implementation Details
- Uses Azure AI Search REST API
- Supports vector search with HNSW algorithm
- Implements proper field mapping to search schema
- Handles batch indexing and updates

#### Azure Search Schema
```json
{
  "name": "educational-content",
  "fields": [
    {"name": "id", "type": "Edm.String", "key": true, "filterable": true},
    {"name": "title", "type": "Edm.String", "searchable": true, "filterable": true},
    {"name": "description", "type": "Edm.String", "searchable": true},
    {"name": "content_type", "type": "Edm.String", "filterable": true, "facetable": true},
    {"name": "subject", "type": "Edm.String", "filterable": true, "facetable": true},
    {"name": "topics", "type": "Collection(Edm.String)", "filterable": true, "facetable": true},
    {"name": "url", "type": "Edm.String"},
    {"name": "source", "type": "Edm.String", "filterable": true},
    {"name": "difficulty_level", "type": "Edm.String", "filterable": true, "facetable": true},
    {"name": "grade_level", "type": "Collection(Edm.Int32)", "filterable": true, "facetable": true},
    {"name": "duration_minutes", "type": "Edm.Int32", "filterable": true, "facetable": true},
    {"name": "keywords", "type": "Collection(Edm.String)", "filterable": true, "facetable": true},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": true, "sortable": true},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": true, "sortable": true},
    {"name": "metadata_content_text", "type": "Edm.String", "searchable": true},
    {"name": "metadata_transcription", "type": "Edm.String", "searchable": true},
    {"name": "metadata_thumbnail_url", "type": "Edm.String"},
    {"name": "page_content", "type": "Edm.String", "searchable": true},
    {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": true, "dimensions": 1536, "vectorSearchProfile": "default-profile"}
  ],
  "vectorSearch": {
    "profiles": [
      {
        "name": "default-profile",
        "algorithm": "default-algorithm"
      }
    ],
    "algorithms": [
      {
        "name": "default-algorithm",
        "kind": "hnsw"
      }
    ]
  }
}
```

### 3.5 LangChain Manager (`langchain_manager.py`)

#### Purpose
Provides a unified interface to LangChain components for content processing and retrieval.

#### Key Features
- Embedding generation
- Document processing and chunking
- Vector search integration
- RAG (Retrieval-Augmented Generation) capabilities
- Conversation and query handling

#### Implementation Details
- Uses LangChain libraries for document processing
- Integrates with Azure OpenAI for embeddings and LLM
- Provides abstraction over Azure AI Search for vector operations
- Implements custom REST API calls for robust indexing

## 4. Processing Workflow

### 4.1 Resource Discovery

1. The Resource Indexer iterates through the configured list of subjects
2. For each subject, it discovers available age groups
3. For each subject-age group combination, it extracts resource links
4. Resource metadata is compiled into a structured index
5. The index is saved to disk for subsequent processing

### 4.2 Content Extraction

1. The Content Extractor loads the resource index
2. For each resource, it extracts detailed content and metadata
3. Content type is determined based on URL and page structure
4. Resource-specific extraction strategies are applied:
   - Articles: Text extraction and summarization
   - Videos: Transcription extraction, thumbnail identification
   - Interactive content: Description and instruction extraction
5. Extracted content is saved with educational metadata

### 4.3 Content Analysis and Indexing

1. The Content Analyzer processes extracted content
2. Educational properties are determined:
   - Difficulty level analysis
   - Grade level appropriateness
   - Topic and keyword extraction
3. Text embeddings are generated for semantic search
4. Content is formatted according to the Azure Search schema
5. Content is indexed in Azure AI Search

## 5. Error Handling and Resilience

### 5.1 Scraping Resilience

- Retry mechanisms for failed page loads
- Multiple selector strategies for content extraction
- Graceful degradation for partially extracted content
- Rate limiting to prevent IP blocking

### 5.2 Processing Error Handling

- Content validation before processing
- Fallback strategies for failed content extraction
- Default values for missing properties
- Detailed logging for failed items

### 5.3 Indexing Error Handling

- Schema validation before indexing
- Field mapping to ensure compatibility
- Batch processing with error tracking
- Retry mechanisms for transient failures

## 6. Performance Considerations

### 6.1 Scraping Performance

- Configurable concurrency levels
- Batch processing of resources
- Progress tracking and resumable operations
- Headless browser mode for production use

### 6.2 Processing Performance

- Asynchronous content extraction
- Parallel processing of content items
- Chunking of large content for efficient processing
- Memory-efficient streaming of large files

### 6.3 Indexing Performance

- Batch indexing for efficient API usage
- Vectorization before indexing for performance
- Index optimization for query performance

## 7. Usage Examples

### 7.1 Running the Full Scraping and Indexing Process

```bash
python backend/scrapers/two_step_scraper.py --step both --subject-limit 7 --headless
```

### 7.2 Running Only the Indexing Step

```bash
python backend/scrapers/two_step_scraper.py --step index --max-pages 10 --headless
```

### 7.3 Running Only the Extraction Step

```bash
python backend/scrapers/two_step_scraper.py --step extract --resource-limit 100 --headless
```

### 7.4 Using the Enhanced Extraction with Azure Integration

```bash
python backend/scrapers/two_step_scraper.py --step both --subject-limit 3 --resource-limit 50
```

## 8. Configuration Options

### 8.1 Environment Variables

```
# Azure Cognitive Services Multi-Service Resource Settings
AZURE_COGNITIVE_ENDPOINT=https://your-cognitive-service.cognitiveservices.azure.com/
AZURE_COGNITIVE_KEY=your-cognitive-service-key

# Azure OpenAI Settings
AZURE_OPENAI_ENDPOINT=https://your-openai-service.openai.azure.com/
AZURE_OPENAI_KEY=your-openai-key
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_DEPLOYMENT=gpt-4-turbo
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Azure AI Search Settings
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=educational-content
```

### 8.2 Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--step` | Which step to run: 'index', 'extract', or 'both' | 'both' |
| `--subject-limit` | Maximum number of subjects to process | None (all) |
| `--resource-limit` | Maximum number of resources per subject | None (all) |
| `--visible` | Run with visible browser (not headless) | False |
| `--max-pages` | Maximum pages to process per subject | 10 |
| `--no-azure` | Disable Azure OpenAI and Azure Search enhancement | False |

## 9. Monitoring and Maintenance

### 9.1 Logging

- Detailed logging of all processing steps
- Error logging with context for debugging
- Performance metrics logging

### 9.2 Scheduled Updates

- Daily incremental scraping for new content
- Weekly full rescanning of all sources
- Monthly reindexing of all content

### 9.3 Monitoring Metrics

- Resources discovered per subject
- Content extraction success rate
- Indexing success rate
- Processing time per resource

## 10. Future Enhancements

### 10.1 Additional Content Sources

- Integration with additional educational content providers
- API-based content ingestion for partnered providers
- User-contributed content integration

### 10.2 Advanced Content Processing

- Image analysis for visual content
- Audio content quality assessment
- Interactive content evaluation
- Learning outcome alignment with standards

### 10.3 Improved Analysis

- Sentiment analysis for content tone
- Age-appropriateness evaluation
- Content diversity metrics
- Engagement prediction models

### 10.4 Enhanced Indexing

- Multi-modal embeddings for mixed content
- Cross-lingual embeddings for multilingual support
- Hierarchical indexing for topic networks
- Collaborative filtering integration for personalization