# backend/utils/report_processor.py
import logging
import asyncio
import os
import tempfile
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient

from config.settings import Settings
from models.student_report import StudentReport, Subject, ReportType
from rag.openai_adapter import get_openai_adapter

settings = Settings()
logger = logging.getLogger(__name__)

class StudentReportProcessor:
    """Process student report documents using Azure AI Document Intelligence,
    extract structured data, and handle PII protection."""
    
    def __init__(self):
        # Initialize Azure Form Recognizer client
        self.document_client = DocumentAnalysisClient(
            endpoint=settings.FORM_RECOGNIZER_ENDPOINT,
            credential=AzureKeyCredential(settings.FORM_RECOGNIZER_KEY)
        ) if settings.FORM_RECOGNIZER_ENDPOINT and settings.FORM_RECOGNIZER_KEY else None
        
        # Initialize OpenAI client when needed
        self.openai_client = None
        
        # Cipher will be initialized asynchronously
        self.cipher = None
        
        # Initialize Azure Blob Storage for document storage (only if connection string is valid)
        self.blob_service_client = None
        if settings.AZURE_STORAGE_CONNECTION_STRING and settings.AZURE_STORAGE_CONNECTION_STRING.strip():
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    settings.AZURE_STORAGE_CONNECTION_STRING
                )
                logger.info("Azure Blob Storage client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Blob Storage client: {e}")
                logger.warning("Document storage in Azure Blob Storage will be disabled")
        else:
            logger.warning("Azure Storage connection string not provided. Document storage will be disabled.")
        
        self.async_blob_client = None
        
        # Initialization flag
        self._initialized = False
    
    async def _init_encryption(self):
        """Initialize encryption for PII data using Azure Key Vault if configured, or local key."""
        logger.info("Initializing encryption...")
        
        # Try to use Azure Key Vault first
        try:
            key_vault_key = await self._get_key_from_keyvault()
            if key_vault_key:
                logger.info("Successfully retrieved key from Key Vault")
                key = key_vault_key
            else:
                logger.info("No Key Vault key available, using local key")
                key = settings.ENCRYPTION_KEY
        except Exception as kv_error:
            logger.error(f"Error retrieving key from Key Vault: {kv_error}")
            logger.info("Falling back to local key")
            key = settings.ENCRYPTION_KEY
        
        if not key:
            logger.warning("No encryption key provided. Sensitive data will not be encrypted.")
            self.cipher = None
            return
            
        # Log key info without revealing actual key
        logger.info(f"Key type: {type(key)}, Key length: {len(str(key)) if key else 0}")
        
        # Add a key verification step
        try:
            # Simple test to see if the key exists and has non-zero length
            if not key or (isinstance(key, str) and len(key.strip()) == 0):
                logger.error("Key is empty or null")
                self.cipher = None
                return
        except Exception as verify_error:
            logger.error(f"Error verifying key: {verify_error}")
            self.cipher = None
            return
        
        try:
            # Check if the key is already in the correct format for Fernet
            # (URL-safe base64-encoded 32-byte key)
            if isinstance(key, str):
                # Try to normalize the key
                modified_key = key.strip()
                
                # Add padding if necessary
                if len(modified_key) % 4 != 0:
                    logger.info("Adding padding to key")
                    modified_key = modified_key + "=" * (-len(modified_key) % 4)
                
                try:
                    # Check if it's a valid Fernet key
                    decoded = base64.urlsafe_b64decode(modified_key)
                    if len(decoded) == 32:
                        logger.info("Key is in the correct format for Fernet")
                        self.cipher = Fernet(modified_key.encode())
                    else:
                        logger.info(f"Key is not 32 bytes (length: {len(decoded)}), deriving proper key")
                        # Derive a key from the provided key or secret
                        salt = b'personalized_learning_salt'  # In production, store this in Key Vault too
                        kdf = PBKDF2HMAC(
                            algorithm=hashes.SHA256(),
                            length=32,
                            salt=salt,
                            iterations=100000,
                        )
                        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
                        self.cipher = Fernet(derived_key)
                except Exception as decode_err:
                    logger.warning(f"Key is not a valid base64 string: {decode_err}")
                    logger.info("Deriving key from the provided value")
                    # Derive a key from the provided key or secret
                    salt = b'personalized_learning_salt'  # In production, store this in Key Vault too
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
                    self.cipher = Fernet(derived_key)
            else:
                logger.warning(f"Key is not a string: {type(key)}")
                # Convert to bytes if needed
                key_bytes = key if isinstance(key, bytes) else str(key).encode()
                
                # Derive a key from the provided key or secret
                salt = b'personalized_learning_salt'  # In production, store this in Key Vault too
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
                self.cipher = Fernet(derived_key)
                
            logger.info("Encryption initialized successfully")
            
            # Test the cipher with a simple encryption/decryption
            try:
                logger.info("Testing encryption functionality...")
                test_message = "encryption_test_message"
                encrypted_test = self.cipher.encrypt(test_message.encode())
                decrypted_test = self.cipher.decrypt(encrypted_test).decode()
                
                if decrypted_test == test_message:
                    logger.info("Encryption test successful")
                else:
                    logger.error(f"Encryption test failed! Expected '{test_message}' but got '{decrypted_test}'")
                    raise ValueError("Encryption test failed: message mismatch")
            except Exception as test_error:
                logger.error(f"Encryption test failed: {test_error}")
                # Create a new key derivation as a fallback
                try:
                    logger.info("Trying fallback key derivation")
                    salt = b'personalized_learning_salt_fallback'
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    key_bytes = key if isinstance(key, bytes) else str(key).encode()
                    derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
                    self.cipher = Fernet(derived_key)
                    
                    # Test again
                    encrypted_test = self.cipher.encrypt(test_message.encode())
                    decrypted_test = self.cipher.decrypt(encrypted_test).decode()
                    if decrypted_test == test_message:
                        logger.info("Fallback encryption test successful")
                    else:
                        logger.error("Fallback encryption test also failed")
                        self.cipher = None
                except Exception as fallback_error:
                    logger.error(f"Fallback encryption initialization failed: {fallback_error}")
                    self.cipher = None
                    
            # End of the encryption initialization
                
        except Exception as e:
            logger.error(f"Error initializing encryption: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            self.cipher = None
            
    async def _get_key_from_keyvault(self):
        """Get encryption key from Azure Key Vault if configured."""
        try:
            if not (settings.AZURE_KEYVAULT_URL and settings.AZURE_KEYVAULT_SECRET_NAME):
                return None
                
            # Import Azure Key Vault client libraries
            try:
                from azure.identity.aio import DefaultAzureCredential
                from azure.keyvault.secrets.aio import SecretClient
            except ImportError:
                logger.warning("Azure Key Vault libraries not installed. Run: pip install azure-identity azure-keyvault-secrets")
                return None
                
            # Get managed identity credential
            credential = DefaultAzureCredential()
            
            # Create a secret client
            client = SecretClient(vault_url=settings.AZURE_KEYVAULT_URL, credential=credential)
            
            # Get the secret
            secret = await client.get_secret(settings.AZURE_KEYVAULT_SECRET_NAME)
            
            # Close the client
            await client.close()
            
            return secret.value
            
        except Exception as e:
            logger.error(f"Error retrieving secret from Key Vault: {e}")
            return None
            
    def _analyze_document_from_url(self, document_url: str):
        """
        Analyze a document from a URL using Azure Document Intelligence.
        
        Args:
            document_url: URL of the document to analyze
            
        Returns:
            Document analysis result or None if analysis failed
        """
        try:
            logger.info(f"Starting document analysis from URL: {document_url}")
            # Begin analysis and wait for result
            poller = self.document_client.begin_analyze_document_from_url(
                "prebuilt-document", document_url
            )
            return poller.result()
        except Exception as e:
            logger.error(f"Error analyzing document from URL: {e}")
            return None
            
    def _analyze_document(self, file_content: bytes):
        """
        Analyze a document from file content using Azure Document Intelligence.
        
        Args:
            file_content: Content of the document to analyze
            
        Returns:
            Document analysis result or None if analysis failed
        """
        try:
            logger.info(f"Starting document analysis from file content ({len(file_content)} bytes)")
            # Begin analysis and wait for result
            poller = self.document_client.begin_analyze_document(
                "prebuilt-document", file_content
            )
            return poller.result()
        except Exception as e:
            logger.error(f"Error analyzing document from content: {e}")
            return None
    
    async def _get_async_blob_client(self):
        """Get or initialize the async blob client."""
        if not self.async_blob_client and settings.AZURE_STORAGE_CONNECTION_STRING and settings.AZURE_STORAGE_CONNECTION_STRING.strip():
            try:
                self.async_blob_client = AsyncBlobServiceClient.from_connection_string(
                    settings.AZURE_STORAGE_CONNECTION_STRING
                )
                logger.info("Async blob client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize async blob client: {e}")
                return None
        return self.async_blob_client
    
    async def ensure_initialized(self):
        """Ensure the processor is initialized."""
        try:
            if not self._initialized:
                logger.info("Initializing report processor...")
                await self._init_encryption()
                logger.info("Initialization complete")
                self._initialized = True
            else:
                logger.debug("Report processor already initialized")
                
            # Verify cipher is available
            if not self.cipher:
                logger.warning("Initialization completed but cipher is not available")
                
        except Exception as init_error:
            logger.error(f"Error during initialization: {init_error}")
            logger.error(f"Initialization traceback: {traceback.format_exc()}")
            # Don't set _initialized to True if initialization failed
            raise
    
    async def encrypt_pii(self, text: str) -> str:
        """Encrypt sensitive PII data."""
        if not text:
            logger.warning("Empty text provided to encrypt_pii")
            return ""
            
        if not isinstance(text, str):
            logger.error(f"Invalid type for text: {type(text)}. Expected string.")
            return str(text) if text is not None else ""
        
        # Ensure initialization is complete    
        try:
            await self.ensure_initialized()
        except Exception as init_error:
            logger.error(f"Error initializing cipher for encryption: {init_error}")
            # Return original text if encryption fails
            return text
        
        if not self.cipher:
            logger.warning("Encryption not configured. Data will be stored unencrypted.")
            return text
        
        try:
            # Attempt encryption
            encrypted = self.cipher.encrypt(text.encode()).decode()
            logger.info("Successfully encrypted data")
            return encrypted
            
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            # Return the original text if encryption fails
            return text
    
    async def decrypt_pii(self, encrypted_text: str) -> str:
        """Decrypt sensitive PII data."""
        if not encrypted_text:
            logger.warning("Empty encrypted text provided to decrypt_pii")
            return ""
            
        if not isinstance(encrypted_text, str):
            logger.error(f"Invalid type for encrypted_text: {type(encrypted_text)}. Expected string.")
            return f"[Decryption Error: Invalid type {type(encrypted_text)}]"
        
        # Ensure initialization is complete    
        try:
            await self.ensure_initialized()
        except Exception as init_error:
            logger.error(f"Error initializing cipher for decryption: {init_error}")
            return f"[Decryption Error: Initialization Failed]"
        
        if not self.cipher:
            logger.warning("Encryption not configured. Data may not be properly encrypted.")
            return encrypted_text
        
        try:
            # Try to clean the encrypted text first - remove any whitespace or newlines
            cleaned_text = encrypted_text.strip()
            
            # Check if it's a valid base64 string for Fernet
            import re
            import base64
            
            # Attempt to fix common base64 issues
            # 1. Ensure valid base64 characters only
            cleaned_text = re.sub(r'[^A-Za-z0-9+/=]', '', cleaned_text)
            
            # 2. Add proper padding if missing
            if len(cleaned_text) % 4 != 0:
                logger.info(f"Adding padding to encrypted text: {len(cleaned_text)} chars") 
                cleaned_text = cleaned_text + "=" * (-len(cleaned_text) % 4)
            
            # Encode for decryption
            encoded_value = cleaned_text.encode()
            
            # Attempt to validate as base64 before decryption
            try:
                # This will fail if not valid base64
                base64.urlsafe_b64decode(cleaned_text)
            except Exception as base64_err:
                logger.warning(f"Value is not valid base64: {base64_err}")
                # Return the original value since we can't decrypt it
                return f"[Invalid Base64: {str(base64_err)[:20]}...]"
                
            # Attempt decryption
            try:
                decrypted = self.cipher.decrypt(encoded_value).decode()
                logger.info("Successfully decrypted data")
                return decrypted
            except Exception as primary_error:
                logger.warning(f"Primary decryption attempt failed: {primary_error}")
                
                # Fallback: Try with original text and padding
                try:
                    logger.info("Trying fallback decryption with original text + padding")
                    padded = encrypted_text + "=" * (-len(encrypted_text) % 4)
                    decrypted = self.cipher.decrypt(padded.encode()).decode()
                    logger.info("Fallback decryption succeeded")
                    return decrypted
                except Exception as fallback_error:
                    logger.error(f"Fallback decryption failed: {fallback_error}")
                    # Let original exception continue to final handler
                    raise primary_error
            
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            logger.error(f"Encrypted text preview: {encrypted_text[:30]}...")
            # Return a placeholder value instead of failing
            return f"[Decryption Error: {str(e)[:50]}...]"
    
    async def process_report_document(self, document_path: str, student_id: str) -> Optional[Dict[str, Any]]:
        """
        Process a student report document using Azure AI Document Intelligence.
        
        Args:
            document_path: Path to the document file
            student_id: ID of the student the report belongs to
            
        Returns:
            Processed StudentReport model or None if processing failed
        """
        if not self.document_client:
            logger.error("Document Analysis client not initialized. Check Form Recognizer credentials.")
            return None
        
        try:
            # Determine if the document is local or a URL
            is_url = document_path.startswith(('http://', 'https://'))
            
            logger.info(f"Processing document: {document_path}")
            
            # Use a thread pool to run the synchronous Document Intelligence operations
            # This prevents blocking the event loop
            loop = asyncio.get_event_loop()
            
            if is_url:
                logger.info("Processing document from URL")
                # Run the sync operation in a thread pool
                result = await loop.run_in_executor(
                    None,
                    lambda: self._analyze_document_from_url(document_path)
                )
            else:
                logger.info("Processing document from file")
                # Read file content
                with open(document_path, "rb") as f:
                    file_content = f.read()
                
                # Run the sync operation in a thread pool
                result = await loop.run_in_executor(
                    None,
                    lambda: self._analyze_document(file_content)
                )
                
            if not result:
                logger.error("Document analysis failed to return results")
                return None
            
            # Extract basic content
            raw_text = result.content
            
            # Store the document in Azure Blob Storage
            document_url = await self._store_document(document_path)
            
            # Extract structured data using LLM
            structured_data = await self._extract_structured_data(raw_text)
            
            # Parse grade level to integer if possible
            grade_level = structured_data.get("grade_level")
            if grade_level and isinstance(grade_level, str):
                try:
                    # Extract numbers from grade level if it contains text
                    import re
                    numbers = re.findall(r'\d+', grade_level)
                    if numbers:
                        grade_level = int(numbers[0])
                    else:
                        # Default to a reasonable value if no number found
                        grade_level = 1
                except (ValueError, TypeError):
                    # If conversion fails, use a default value
                    grade_level = 1
            
            # Create StudentReport object
            report = StudentReport(
                student_id=student_id,
                report_type=structured_data.get("report_type", ReportType.PRIMARY),
                school_name=structured_data.get("school_name"),
                school_year=structured_data.get("school_year"),
                term=structured_data.get("term"),
                grade_level=grade_level,
                teacher_name=structured_data.get("teacher_name"),
                report_date=structured_data.get("report_date"),
                general_comments=structured_data.get("general_comments"),
                attendance=structured_data.get("attendance", {}),
                subjects=self._parse_subjects(structured_data.get("subjects", [])),
                raw_extracted_text=raw_text,
                document_url=document_url,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Encrypt PII fields
            encrypted_fields = {}
            for field in ["teacher_name", "general_comments"]:
                if getattr(report, field):
                    encrypted_fields[field] = await self.encrypt_pii(getattr(report, field))
                    setattr(report, field, None)  # Clear the original field
            
            # Convert encrypted fields to JSON string for storage in Azure Search
            report.encrypted_fields = json.dumps(encrypted_fields)
            
            # Generate embedding for the report
            if not self.openai_client:
                self.openai_client = await get_openai_adapter()
                
            embedding = await self.openai_client.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=self._prepare_text_for_embedding(report, raw_text)
            )
            
            # Create StudentReportWithEmbedding object
            report_with_embedding = {
                **report.dict(),
                "embedding": embedding
            }
            
            return report_with_embedding
            
        except Exception as e:
            logger.error(f"Error processing student report document: {e}")
            return None
    
    async def _store_document(self, document_path: str) -> Optional[str]:
        """
        Store the document in Azure Blob Storage.
        
        Args:
            document_path: Path to the document file
            
        Returns:
            URL to the stored document or None if storage failed
        """
        # Skip storage if Azure Storage is not configured
        if not self.blob_service_client and not settings.AZURE_STORAGE_CONNECTION_STRING:
            logger.warning("Azure Blob Storage not configured. Document will not be stored.")
            # Return document path as a fallback (for local testing)
            return f"file://{document_path}" if not document_path.startswith(('http://', 'https://')) else document_path
            
        try:
            # Get blob client
            blob_client = await self._get_async_blob_client()
            if not blob_client:
                logger.warning("Async blob client not available. Using local file path instead.")
                return f"file://{document_path}" if not document_path.startswith(('http://', 'https://')) else document_path
                
            # Create the container if it doesn't exist
            container_name = settings.REPORT_CONTAINER_NAME or "student-reports"
            container_client = blob_client.get_container_client(container_name)
            try:
                # Check if container exists first
                exists = False
                try:
                    # Try to get container properties to check if it exists
                    await container_client.get_container_properties()
                    exists = True
                except Exception:
                    # Container doesn't exist
                    exists = False
                
                # Create the container if it doesn't exist
                if not exists:
                    await container_client.create_container()
                    logger.info(f"Container {container_name} created successfully")
                else:
                    logger.info(f"Container {container_name} already exists")
            except Exception as e:
                logger.warning(f"Error with container: {e}")
                # Return local path as fallback
                return f"file://{document_path}" if not document_path.startswith(('http://', 'https://')) else document_path
            
            # Generate a unique blob name
            blob_name = f"{uuid.uuid4()}-{os.path.basename(document_path)}"
            
            # Get blob client
            blob_client = container_client.get_blob_client(blob_name)
            
            # Determine content type
            content_type = "application/pdf"
            if document_path.lower().endswith(".docx"):
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif document_path.lower().endswith((".jpg", ".jpeg")):
                content_type = "image/jpeg"
            elif document_path.lower().endswith(".png"):
                content_type = "image/png"
            
            # Upload the file
            if document_path.startswith(('http://', 'https://')):
                # Download from URL first
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(document_path) as response:
                        if response.status == 200:
                            file_data = await response.read()
                            await blob_client.upload_blob(
                                file_data,
                                content_settings=ContentSettings(content_type=content_type),
                                overwrite=True
                            )
            else:
                # Upload local file
                with open(document_path, "rb") as data:
                    await blob_client.upload_blob(
                        data,
                        content_settings=ContentSettings(content_type=content_type),
                        overwrite=True
                    )
            
            # Return the URL
            return f"https://{blob_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}"
            
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            # Return the local path as a fallback (for testing)
            return f"file://{document_path}" if not document_path.startswith(('http://', 'https://')) else document_path
    
    async def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """
        Extract structured data from raw text using Azure OpenAI.
        
        Args:
            text: Raw text extracted from the document
            
        Returns:
            Dictionary of structured data extracted from the text
        """
        if not self.openai_client:
            self.openai_client = await get_openai_adapter()
        
        try:
            # Prepare the prompt
            prompt = f"""
            Extract structured information from this student report. 
            Identify the following information:
            - report_type (primary, secondary, special_ed, standardized_test)
            - school_name
            - school_year
            - term
            - grade_level (as a number)
            - teacher_name
            - report_date (in YYYY-MM-DD format)
            - subjects (list of subjects with the following structure:
                - name: string
                - grade: string
                - comments: string
                - achievement_level: string
                - areas_for_improvement: array of strings (IMPORTANT: must be an array/list, not a single string)
                - strengths: array of strings (IMPORTANT: must be an array/list, not a single string)
            )
            - general_comments: string
            - attendance (object with:
                - days_present: number
                - days_absent: number
                - days_late: number
            )
            
            IMPORTANT FORMATTING INSTRUCTIONS:
            1. Format the response as a valid JSON object
            2. For arrays like areas_for_improvement and strengths, always use proper JSON array syntax like ["item1", "item2"]
            3. Do not use single strings where arrays are expected
            4. For grade_level, convert to a numeric value (e.g., "Fifth Grade" should be 5)
            
            Here is the report text:
            {text[:4000]}  # Truncate to stay within token limits
            """
            
            # Get the completion
            response = await self.openai_client.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            content = response["choices"][0]["message"]["content"]
            structured_data = json.loads(content)
            
            # Try to convert report_date to datetime if provided
            if "report_date" in structured_data and structured_data["report_date"]:
                try:
                    structured_data["report_date"] = datetime.fromisoformat(structured_data["report_date"])
                except ValueError:
                    logger.warning(f"Could not parse report date: {structured_data['report_date']}")
                    structured_data["report_date"] = None
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return {}
    
    def _parse_subjects(self, subjects_data: List[Dict[str, Any]]) -> List[Subject]:
        """
        Parse subject data from the structured data.
        
        Args:
            subjects_data: List of subject dictionaries
            
        Returns:
            List of Subject models
        """
        subjects = []
        for subject_data in subjects_data:
            try:
                # Ensure areas_for_improvement and strengths are lists
                areas_for_improvement = subject_data.get("areas_for_improvement", [])
                if isinstance(areas_for_improvement, str):
                    # If it's a string, convert to a list with a single item
                    areas_for_improvement = [areas_for_improvement]
                elif not isinstance(areas_for_improvement, list):
                    # If it's neither a string nor a list, default to empty list
                    areas_for_improvement = []
                
                strengths = subject_data.get("strengths", [])
                if isinstance(strengths, str):
                    # If it's a string, convert to a list with a single item
                    strengths = [strengths]
                elif not isinstance(strengths, list):
                    # If it's neither a string nor a list, default to empty list
                    strengths = []
                
                subject = Subject(
                    name=subject_data.get("name", "Unknown"),
                    grade=subject_data.get("grade"),
                    comments=subject_data.get("comments"),
                    achievement_level=subject_data.get("achievement_level"),
                    areas_for_improvement=areas_for_improvement,
                    strengths=strengths
                )
                subjects.append(subject)
            except Exception as e:
                logger.error(f"Error parsing subject data: {e}")
        
        return subjects
    
    def _prepare_text_for_embedding(self, report: StudentReport, raw_text: str) -> str:
        """
        Prepare report text for embedding.
        
        Args:
            report: StudentReport object
            raw_text: Raw extracted text
            
        Returns:
            Text prepared for embedding
        """
        # Combine relevant fields
        text_parts = [
            f"Student Report for Student ID: {report.student_id}",
            f"Report Type: {report.report_type}",
        ]
        
        if report.school_name:
            text_parts.append(f"School: {report.school_name}")
        
        if report.school_year:
            text_parts.append(f"School Year: {report.school_year}")
        
        if report.term:
            text_parts.append(f"Term: {report.term}")
        
        if report.grade_level:
            text_parts.append(f"Grade Level: {report.grade_level}")
        
        # Add subject information
        if report.subjects:
            text_parts.append("Subjects:")
            for subject in report.subjects:
                subject_text = f"- {subject.name}"
                if subject.grade:
                    subject_text += f", Grade: {subject.grade}"
                if subject.achievement_level:
                    subject_text += f", Achievement Level: {subject.achievement_level}"
                text_parts.append(subject_text)
        
        # Include a portion of the raw text (truncated if too long)
        if raw_text:
            if len(raw_text) > 1000:
                text_parts.append(f"Content Excerpt: {raw_text[:1000]}...")
            else:
                text_parts.append(f"Content: {raw_text}")
        
        return "\n".join(text_parts)

# Create a singleton instance
report_processor = None

async def get_report_processor():
    """Get or create the report processor singleton."""
    global report_processor
    logger.info("====== START: Getting report processor instance ======")
    
    # Return current instance if already initialized
    if report_processor is not None and report_processor._initialized:
        logger.info("Using existing initialized StudentReportProcessor instance")
        return report_processor
    
    # Try to create and/or initialize the processor
    try:
        # Create the processor if it doesn't exist
        if report_processor is None:
            logger.info("Creating new StudentReportProcessor instance")
            try:
                report_processor = StudentReportProcessor()
                logger.info("StudentReportProcessor instance created successfully")
            except Exception as create_error:
                logger.error(f"CRITICAL ERROR: Failed to create StudentReportProcessor: {create_error}")
                logger.error(f"Creation traceback: {traceback.format_exc()}")
                return None
        else:
            logger.info("Using existing StudentReportProcessor instance (needs initialization)")
        
        # Ensure the processor is initialized
        try:
            logger.info("Starting processor initialization")
            await report_processor.ensure_initialized()
            logger.info("Report processor initialized successfully")
        except Exception as init_error:
            logger.error(f"CRITICAL ERROR: Failed to initialize StudentReportProcessor: {init_error}")
            logger.error(f"Initialization traceback: {traceback.format_exc()}")
            
            # Return the instance even if not fully initialized
            # Some functionality might still work without encryption
            logger.warning("Returning partially initialized processor (encryption may not work)")
            
        logger.info("====== END: Report processor setup complete ======")
        return report_processor
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR: Unexpected error creating/initializing report processor: {e}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        # Return None instead of raising, so API endpoints can handle gracefully
        logger.warning("Returning None due to critical initialization error")
        return None