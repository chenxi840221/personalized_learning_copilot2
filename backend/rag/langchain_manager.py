# backend/rag/langchain_manager.py
"""
LangChain integration for the Personalized Learning Co-pilot.
This module provides a simplified interface to LangChain components
with Azure OpenAI integration and handles all vector operations.
"""

import logging
from typing import List, Dict, Any, Optional, Union
import os
import sys

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)  # Add project root to path

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class LangChainManager:
    """
    Manager for LangChain components using Azure OpenAI.
    Provides access to language models, embeddings, and vector stores.
    """
    
    def __init__(self):
        """Initialize the LangChain manager with configured settings."""
        self.llm = None
        self.embeddings = None
        self.vector_store = None
        self.retriever = None
        self.conversation_chain = None
        self.conversation_memory = None
    
    def initialize(self):
        """Initialize LangChain components."""
        try:
            # Initialize Azure OpenAI LLM
            self.llm = AzureChatOpenAI(
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_KEY,
                temperature=0.7,
                streaming=True
            )
            
            # Initialize Azure OpenAI Embeddings
            self.embeddings = AzureOpenAIEmbeddings(
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_KEY,
            )
            
            # Initialize conversation memory
            self.conversation_memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            
            # Setup Azure AI Search vector store if settings are available
            if settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY:
                self.vector_store = AzureSearch(
                    azure_search_endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    azure_search_key=settings.AZURE_SEARCH_KEY,
                    index_name=settings.AZURE_SEARCH_INDEX_NAME,
                    embedding_function=self.embeddings.embed_query,
                    vector_field_name="embedding",  # Explicitly set vector field name
                    text_field_name="page_content",  # Use page_content instead of "content"
                    fields_mapping={
                        "content": "page_content",  # Map legacy 'content' field to 'page_content'
                        "content_text": "metadata_content_text",  # Map text content to metadata
                        "transcription": "metadata_transcription"  # Map transcriptions to metadata
                    }
                )
                
                # Create retriever
                self.retriever = self.vector_store.as_retriever(
                    search_kwargs={"k": 5}
                )
                
                # Initialize the RAG conversation chain
                self.conversation_chain = ConversationalRetrievalChain.from_llm(
                    llm=self.llm,
                    retriever=self.retriever,
                    memory=self.conversation_memory
                )
                
            logger.info("LangChain components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing LangChain components: {e}")
            raise
    
    async def generate_completion(
        self, 
        prompt: str, 
        system_message: str = "You are a helpful educational assistant.",
        temperature: float = 0.7
    ) -> str:
        """
        Generate text completion using Azure OpenAI.
        
        Args:
            prompt: User prompt
            system_message: System message to set the context
            temperature: Temperature for generation (0-1)
            
        Returns:
            Generated text
        """
        if not self.llm:
            self.initialize()
            
        try:
            # Setup chat messages
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            # Generate response
            response = await self.llm.ainvoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return f"Error generating response: {str(e)}"
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using LangChain's embedding model.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        if not self.embeddings:
            self.initialize()
            
        try:
            # Generate embedding
            embedding = await self.embeddings.aembed_query(text)
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return an empty embedding of the correct dimension
            return [0.0] * 1536  # Default dimension for text-embedding-ada-002
    
    async def generate_rag_response(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using Retrieval-Augmented Generation (RAG).
        
        Args:
            query: User query
            chat_history: Optional chat history
            
        Returns:
            Dictionary with response and source documents
        """
        if not self.conversation_chain:
            self.initialize()
            if not self.conversation_chain:
                # Fall back to regular completion if RAG is not available
                response = await self.generate_completion(query)
                return {
                    "answer": response,
                    "source_documents": []
                }
                
        try:
            # Format chat history if provided
            formatted_history = []
            if chat_history:
                for message in chat_history:
                    if message.get("role") == "user":
                        formatted_history.append((message.get("content", ""), ""))
                    elif message.get("role") == "assistant":
                        if formatted_history:
                            formatted_history[-1] = (formatted_history[-1][0], message.get("content", ""))
                        else:
                            formatted_history.append(("", message.get("content", "")))
            
            # Generate RAG response
            response = await self.conversation_chain.ainvoke({
                "question": query,
                "chat_history": formatted_history
            })
            
            # Extract source documents
            source_documents = response.get("source_documents", [])
            
            return {
                "answer": response.get("answer", ""),
                "source_documents": source_documents
            }
            
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            # Fall back to regular completion
            response = await self.generate_completion(query)
            return {
                "answer": response,
                "source_documents": []
            }
    
    async def add_documents(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Add documents to the vector store.
        
        Args:
            texts: List of text content
            metadatas: Optional metadata for each text
            
        Returns:
            Success status
        """
        if not self.vector_store:
            self.initialize()
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return False
            
        try:
            # Create Document objects
            documents = []
            for i, text in enumerate(texts):
                metadata = {}
                if metadatas and i < len(metadatas):
                    metadata = metadatas[i].copy()  # Make a copy to avoid modifying the original
                
                # Make sure we're not using 'content' field (use page_content instead)
                # This field will be recognized by LangChain and mapped to the correct field in Azure Search
                doc = Document(page_content=text, metadata=metadata)
                documents.append(doc)
            
            # Add documents to vector store with the correct field mapping
            # Explicitly specify the text_field to ensure we're using the right field name
            self.vector_store.add_documents(
                documents,
                vector_field_name="embedding",
                text_field_name="page_content"  # Make sure this matches your Azure Search schema
            )
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            return False
    
    async def search_documents(self, query: str, filter: Optional[str] = None, k: int = 5) -> List[Document]:
        """
        Search for documents using a query string.
        
        Args:
            query: Query string
            filter: Optional filter expression
            k: Number of results to return
            
        Returns:
            List of matching documents
        """
        if not self.vector_store:
            self.initialize()
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return []
            
        try:
            # Search for documents
            search_kwargs = {"k": k}
            if filter:
                search_kwargs["filter"] = filter
                
            documents = self.vector_store.similarity_search(query, **search_kwargs)
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    async def process_document(self, document_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> bool:
        """
        Process a document and add it to the vector store.
        
        Args:
            document_path: Path to the document
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
            
        Returns:
            Success status
        """
        if not self.vector_store:
            self.initialize()
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return False
            
        try:
            from langchain_community.document_loaders import TextLoader
            
            # Load document
            loader = TextLoader(document_path)
            documents = loader.load()
            
            # Split text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            chunks = text_splitter.split_documents(documents)
            
            # Add to vector store
            self.vector_store.add_documents(documents=chunks)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return False
    
    async def generate_personalized_learning_plan(
        self,
        student_profile: Dict[str, Any],
        subject: str,
        available_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a personalized learning plan using LangChain.
        
        Args:
            student_profile: Student information
            subject: Subject for the learning plan
            available_content: Available content resources
            
        Returns:
            Personalized learning plan
        """
        if not self.llm:
            self.initialize()
            
        try:
            # Format content resources for the prompt
            resources_text = ""
            for i, content in enumerate(available_content):
                resources_text += f"""
                Content {i+1}:
                - ID: {content.get('id', 'unknown')}
                - Title: {content.get('title', 'Untitled')}
                - Type: {content.get('content_type', 'unknown')}
                - Difficulty: {content.get('difficulty_level', 'unknown')}
                - Description: {content.get('description', 'No description')}
                """
                
            # Construct the prompt
            profile_text = f"""
            Student Profile:
            - Name: {student_profile.get('full_name', student_profile.get('username', 'Student'))}
            - Grade Level: {student_profile.get('grade_level', 'Unknown')}
            - Learning Style: {student_profile.get('learning_style', 'Mixed')}
            - Interests: {', '.join(student_profile.get('subjects_of_interest', []))}
            """
            
            prompt_template = f"""
            Create a personalized learning plan for the following student:
            
            {profile_text}
            
            The learning plan should focus on: {subject}
            
            Available resources:
            {resources_text}
            
            The learning plan should include:
            1. A title
            2. A brief description
            3. 4-5 learning activities that use the available resources
            4. Each activity should include a title, description, duration, and reference to a resource ID if applicable
            
            Format the response as JSON with the following structure:
            {{
                "title": "Learning Plan Title",
                "description": "Brief description of the plan",
                "subject": "{subject}",
                "activities": [
                    {{
                        "title": "Activity Title",
                        "description": "Activity description",
                        "content_id": "reference to resource ID or null",
                        "duration_minutes": time in minutes,
                        "order": order number
                    }}
                ]
            }}
            """
            
            # Create prompt template
            messages = [
                {"role": "system", "content": "You are an expert educational assistant that creates personalized learning plans."},
                {"role": "user", "content": prompt_template}
            ]
            
            # Generate learning plan
            response = await self.llm.ainvoke(messages)
            
            # Parse the JSON result
            import json
            try:
                # Extract JSON if it's within a code block
                result = response.content
                if "```json" in result:
                    json_start = result.find("```json") + 7
                    json_end = result.find("```", json_start)
                    result = result[json_start:json_end].strip()
                elif "```" in result:
                    json_start = result.find("```") + 3
                    json_end = result.find("```", json_start)
                    result = result[json_start:json_end].strip()
                    
                learning_plan = json.loads(result)
                return learning_plan
                
            except json.JSONDecodeError:
                logger.error(f"Error parsing learning plan JSON: {result}")
                # Return the raw text as a fallback
                return {
                    "title": f"{subject} Learning Plan",
                    "description": f"A learning plan for {subject}",
                    "subject": subject,
                    "raw_response": result,
                    "activities": []
                }
            
        except Exception as e:
            logger.error(f"Error generating learning plan: {e}")
            return {
                "title": f"{subject} Learning Plan",
                "description": f"An error occurred while generating the learning plan: {str(e)}",
                "subject": subject,
                "activities": []
            }

# Singleton instance
langchain_manager = None

def get_langchain_manager():
    """Get or create the LangChain manager singleton."""
    global langchain_manager
    if langchain_manager is None:
        langchain_manager = LangChainManager()
        langchain_manager.initialize()
    return langchain_manager