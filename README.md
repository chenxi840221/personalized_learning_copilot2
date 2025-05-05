# Personalized Learning Co-pilot

A comprehensive AI-powered educational platform that provides tailored learning experiences based on student profiles using Retrieval-Augmented Generation (RAG).

## Overview

The Personalized Learning Co-pilot is an educational technology solution that:

- Creates personalized learning plans using AI and student profile data
- Recommends relevant educational resources based on learning style, grade level, and interests
- Provides an interactive dashboard for tracking learning progress
- Supports various content types including videos, articles, interactive exercises, and quizzes
- Utilizes advanced RAG (Retrieval-Augmented Generation) techniques to deliver relevant content

## Key Features

- **Personalized Learning Plans**: AI-generated learning paths customized to individual student needs
- **Content Recommendations**: Intelligent recommendation system based on student profile and learning progress
- **Progress Tracking**: Comprehensive dashboard to track completion and mastery across subjects
- **User Profiles**: Student profiles with learning style detection, grade level, and subject preferences
- **Multimedia Support**: Integration with various content types including videos, audio, and interactive elements
- **Responsive Design**: Mobile-friendly interface accessible on any device

## Technologies

### Frontend
- **React**: Modern component-based UI library
- **React Router**: Client-side routing
- **TailwindCSS**: Utility-first CSS framework for responsive design
- **Axios**: Promise-based HTTP client for API requests

### Backend
- **FastAPI**: High-performance Python web framework
- **LangChain**: Framework for developing applications with LLMs
- **Azure OpenAI**: AI services for content generation and embeddings
- **Azure AI Search**: Vector database for semantic search capabilities
- **Azure Cognitive Services**: For content processing and analysis

### Infrastructure
- **Docker**: Containerization for consistent deployment
- **Azure**: Cloud hosting and services
- **Azure AI Search**: Vector database for content storage and semantic search

## Architecture

![Architecture Diagram](https://via.placeholder.com/800x400?text=Architecture+Diagram)

The system follows a modern microservices architecture:

1. **User Interface Layer**: React-based frontend with responsive design
2. **API Layer**: FastAPI backend providing RESTful endpoints
3. **AI Services Layer**: Integration with Azure OpenAI and LangChain
4. **Persistence Layer**: Azure AI Search for both structured data and vector search
5. **Content Processing Layer**: Services for analyzing and processing educational content

## Getting Started

### Prerequisites

- Node.js 16+
- Python 3.8+
- Docker and Docker Compose
- Azure OpenAI Service access
- Azure AI Search

### Local Development Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/personalized-learning-copilot.git
cd personalized-learning-copilot
```

2. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Start the backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

4. Start the frontend
```bash
cd frontend
npm install
npm start
```

### Docker Setup

For a complete deployment with all services:

```bash
docker-compose up -d
```

This will start:
- Frontend on port 3000
- Backend API on port 8000
- All required services

## API Documentation

Once the backend is running, you can access the API documentation at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Content Personalization

The system personalizes learning content using:

1. **Student Profile Analysis**: Analyzing learning style, grade level, and interests
2. **Content Embeddings**: Vector representations of educational content for semantic search
3. **Learning Progress Data**: Adapting recommendations based on completed activities
4. **RAG Techniques**: Combining retrieval of relevant content with AI-generated learning plans

## Demo and Screenshots

### Dashboard
![Dashboard](https://via.placeholder.com/800x400?text=Dashboard+Screenshot)

### Learning Plan
![Learning Plan](https://via.placeholder.com/800x400?text=Learning+Plan+Screenshot)

### Content Recommendations
![Content Recommendations](https://via.placeholder.com/800x400?text=Content+Recommendations+Screenshot)

## Future Enhancements

- **Advanced Analytics**: Detailed insights into learning patterns and optimization
- **Collaborative Learning**: Group learning features and peer recommendations
- **Content Creation**: AI-assisted content generation for educators
- **Mobile App**: Native mobile applications for Android and iOS
- **Offline Mode**: Support for offline learning with synchronization
- **AR/VR Integration**: Immersive learning experiences

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The ABC Education platform for educational content
- The Azure OpenAI team for AI capabilities
- The educational technology community for inspiration and standards# personalized_learning_copilot2
