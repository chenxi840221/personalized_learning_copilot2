# backend/rag/azure_langchain_integration.py
"""
Azure-specific LangChain integration for the Personalized Learning Co-pilot.
This module provides specialized components that connect LangChain with 
Azure OpenAI and Azure AI Search services.
"""

import logging
import os
import asyncio
from typing import List, Dict, Any, Optional

# LangChain imports
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_community.retrievers import AzureAISearchRetriever
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Azure imports
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient

# Internal imports
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class AzureLangChainIntegration:
    """
    Integration between LangChain, Azure OpenAI, and Azure AI Search.
    Provides specialized components configured for Azure services.
    """
    
    def __init__(self):
        """Initialize the Azure LangChain integration."""
        self.llm = None
        self.embeddings = None
        self.vector_store = None
        self.search_client = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize LangChain components with Azure services."""
        if self.initialized:
            return
            
        try:
            # Initialize Azure OpenAI Chat model
            self.llm = AzureChatOpenAI(
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_KEY,
                temperature=0.7,
            )
            
            # Initialize Azure OpenAI Embeddings
            self.embeddings = AzureOpenAIEmbeddings(
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_KEY,
            )
            
            # Initialize Azure AI Search client if settings are available
            if (settings.AZURE_SEARCH_ENDPOINT and 
                settings.AZURE_SEARCH_KEY and 
                settings.AZURE_SEARCH_INDEX_NAME):
                
                self.search_client = SearchClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    index_name=settings.AZURE_SEARCH_INDEX_NAME,
                    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
                )
                
                # Initialize vector store with Azure AI Search
                self.vector_store = AzureSearch(
                    azure_search_endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    azure_search_key=settings.AZURE_SEARCH_KEY,
                    index_name=settings.AZURE_SEARCH_INDEX_NAME,
                    embedding_function=self.embeddings.embed_query,
                )
                
                logger.info("Azure AI Search integration initialized")
            else:
                logger.warning("Azure AI Search settings not available, vector search disabled")
            
            self.initialized = True
            logger.info("Azure LangChain integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Azure LangChain integration: {e}")
            raise
    
    async def create_rag_chain(self, system_prompt: str = None):
        """
        Create a Retrieval-Augmented Generation chain using Azure AI Search.
        
        Args:
            system_prompt: Optional system prompt to set context
            
        Returns:
            A RAG chain that can be used for question answering
        """
        if not self.initialized:
            await self.initialize()
            
        if not self.vector_store:
            raise ValueError("Vector store not initialized, cannot create RAG chain")
            
        try:
            # Default system prompt if none provided
            if not system_prompt:
                system_prompt = """You are an educational assistant for a personalized learning system.
                Use the retrieved documents to provide accurate, helpful responses to questions.
                For students in primary and secondary education, adapt your language to be age-appropriate.
                If you don't know the answer, say so - don't make up information."""
            
            # Create retriever
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_template(
                """
                <context>
                {context}
                </context>
                
                Given the context information and not prior knowledge, answer the question.
                Question: {question}
                """
            )
            
            # Create RAG chain
            chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
            )
            
            return chain
            
        except Exception as e:
            logger.error(f"Error creating RAG chain: {e}")
            raise
    
    async def create_conversational_rag_chain(self):
        """
        Create a conversational RAG chain with memory.
        
        Returns:
            A conversational RAG chain
        """
        if not self.initialized:
            await self.initialize()
            
        if not self.vector_store:
            raise ValueError("Vector store not initialized, cannot create conversational RAG chain")
            
        try:
            # Create retriever
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
            
            # Create memory
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            
            # Create chain
            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=memory
            )
            
            return chain
            
        except Exception as e:
            logger.error(f"Error creating conversational RAG chain: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            # Generate embeddings
            embeddings = await self.embeddings.aembed_documents(texts)
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    async def index_documents(self, documents: List[Dict[str, Any]], owner_id: Optional[str] = None) -> bool:
        """
        Index documents in Azure AI Search using LangChain.
        
        Args:
            documents: List of documents to index
            owner_id: Optional owner ID to assign to all documents (for access control)
            
        Returns:
            Success status
        """
        if not self.initialized:
            await self.initialize()
            
        if not self.vector_store:
            raise ValueError("Vector store not initialized, cannot index documents")
            
        try:
            # Process documents with embeddings
            texts = [doc.get("text", "") or doc.get("content", "") for doc in documents]
            metadatas = []
            
            for i, doc in enumerate(documents):
                # Start with the existing metadata excluding text/content fields
                metadata = {"id": doc.get("id", str(i)), **{k: v for k, v in doc.items() if k not in ["text", "content"]}}
                
                # Ensure owner_id is set for each document
                if "owner_id" not in metadata and owner_id:
                    metadata["owner_id"] = owner_id
                elif "owner_id" not in metadata:
                    logger.warning(f"Document {metadata.get('id')} has no owner_id field and no default provided")
                
                metadatas.append(metadata)
            
            # Add documents to the vector store
            await asyncio.to_thread(self.vector_store.add_texts, texts, metadatas)
            
            logger.info(f"Successfully indexed {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
            return False
    
    async def search_documents(
        self, 
        query: str, 
        filter: Optional[str] = None, 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search documents in Azure AI Search using semantic search.
        
        Args:
            query: Search query
            filter: Optional filter expression
            top_k: Number of results to return
            
        Returns:
            List of matching documents
        """
        if not self.initialized:
            await self.initialize()
            
        if not self.vector_store:
            raise ValueError("Vector store not initialized, cannot search documents")
            
        try:
            # Generate embedding for query
            query_embedding = await self.embeddings.aembed_query(query)
            
            # Perform vector search
            search_results = await self._similarity_search_with_vector(
                embedding=query_embedding,
                k=top_k,
                filter=filter
            )
            
            # Format results
            formatted_results = []
            for doc, score in search_results:
                result = {
                    "id": doc.metadata.get("id", ""),
                    "content": doc.page_content,
                    "score": score,
                    **doc.metadata
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    async def _similarity_search_with_vector(
        self, 
        embedding: List[float], 
        k: int = 5, 
        filter: Optional[str] = None
    ) -> List[tuple]:
        """
        Perform similarity search using a vector embedding.
        
        Args:
            embedding: Vector embedding
            k: Number of results to return
            filter: Optional filter expression
            
        Returns:
            List of (document, score) tuples
        """
        try:
            if hasattr(self.vector_store, "similarity_search_with_score_by_vector"):
                # Use synchronous method with await
                result = await asyncio.to_thread(
                    self.vector_store.similarity_search_with_score_by_vector,
                    embedding,
                    k=k,
                    filter=filter
                )
                return result
            else:
                # Fallback to standard method
                docs = await asyncio.to_thread(
                    self.vector_store.similarity_search_by_vector,
                    embedding,
                    k=k,
                    filter=filter
                )
                return [(doc, 1.0) for doc in docs]  # Default score of 1.0
                
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    async def generate_learning_plan_with_rag(
        self,
        student_profile: Dict[str, Any],
        subject: str,
        available_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a personalized learning plan using RAG to incorporate educational best practices.
        
        Args:
            student_profile: Student information
            subject: Subject for the learning plan
            available_content: Available content resources
            
        Returns:
            A personalized learning plan
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            # Format content resources
            formatted_content = "\n\n".join([
                f"Resource {i+1}:\n"
                f"Title: {content.get('title', 'Untitled')}\n"
                f"ID: {content.get('id', f'resource_{i}')}\n"
                f"Type: {content.get('content_type', 'unknown')}\n"
                f"Description: {content.get('description', 'No description')}"
                for i, content in enumerate(available_content[:10])  # Limit to 10 resources
            ])
            
            # Format student profile
            formatted_profile = (
                f"Student Grade Level: {student_profile.get('grade_level', 'Unknown')}\n"
                f"Learning Style: {student_profile.get('learning_style', 'Mixed')}\n"
                f"Interests: {', '.join(student_profile.get('subjects_of_interest', []))}"
            )
            
            # Create prompt template for learning plan generation
            prompt = PromptTemplate.from_template(
                """
                You are an expert educational planner. Create a personalized learning plan for a student with
                the following profile:
                {student_profile}
                
                The plan should focus on the subject: {subject}
                
                Available educational resources:
                {resources}
                
                Create a comprehensive learning plan that includes:
                1. An appropriate title
                2. A brief description
                3. 4-6 learning activities that use the available resources
                4. Each activity should:
                   - Have a title and description
                   - Reference a specific resource ID where applicable
                   - Specify an estimated duration in minutes
                   - Be in a logical sequence
                
                Format your response as JSON with the following structure:
                {{
                    "title": "Learning Plan Title",
                    "description": "Brief description of the learning plan",
                    "subject": "{subject}",
                    "topics": ["topic1", "topic2"...],
                    "activities": [
                        {{
                            "title": "Activity Title",
                            "description": "Activity description",
                            "content_id": "resource_id or null",
                            "duration_minutes": estimated_minutes,
                            "order": sequence_number
                        }},
                        ...
                    ]
                }}
                
                Return ONLY the JSON with no additional text.
                """
            )
            
            # Run the prompt through the language model
            chain = prompt | self.llm | StrOutputParser()
            
            result = await chain.ainvoke({
                "student_profile": formatted_profile,
                "subject": subject,
                "resources": formatted_content
            })
            
            # Parse the JSON result
            import json
            
            try:
                # Clean up the response to ensure it's valid JSON
                json_start = result.find("{")
                json_end = result.rfind("}")
                if json_start >= 0 and json_end > json_start:
                    clean_json = result[json_start:json_end+1]
                    learning_plan = json.loads(clean_json)
                else:
                    learning_plan = json.loads(result)
                    
                return learning_plan
                
            except json.JSONDecodeError:
                logger.error(f"Error parsing learning plan JSON: {result}")
                # Return a basic plan with the raw response
                return {
                    "title": f"{subject} Learning Plan",
                    "description": f"A learning plan for {subject}",
                    "subject": subject,
                    "topics": [subject],
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
azure_langchain = None

async def get_azure_langchain():
    """Get or create the Azure LangChain integration singleton."""
    global azure_langchain
    if azure_langchain is None:
        azure_langchain = AzureLangChainIntegration()
        await azure_langchain.initialize()
    return azure_langchain