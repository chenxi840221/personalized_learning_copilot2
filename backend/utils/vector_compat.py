# backend/utils/vector_compat.py

"""
Compatibility module for Azure Search Vector class.
This module provides the Vector class for different versions of the Azure Search SDK.
Updated for Azure AI Search 2023-07-01-Preview API.
"""

import logging
logger = logging.getLogger(__name__)

try:
    # Try to import Vector from azure.search.documents.models
    from azure.search.documents.models import Vector
    USING_SDK_VERSION = "Standard"
except ImportError:
    try:
        # Try to import Vector from models package
        from azure.search.documents._generated.models import Vector
        USING_SDK_VERSION = "Generated"
    except ImportError:
        try:
            # Try to import from beta package
            from azure.search.documents.aio._search_client import Vector
            USING_SDK_VERSION = "Beta-aio"
        except ImportError:
            try:
                # Try another possible location
                from azure.search.documents._search_client import Vector
                USING_SDK_VERSION = "Beta-sync"
            except ImportError:
                # Define our own Vector class if none is available
                class Vector:
                    """
                    Vector class for Azure Search vector search.
                    This is a compatibility implementation for when the SDK doesn't provide it.
                    """
                    def __init__(self, value, k=None, fields=None, exhaustive=None):
                        self.value = value
                        self.k = k
                        self.fields = fields
                        self.exhaustive = exhaustive
                    
                    def __repr__(self):
                        return (f"Vector(value=[...], k={self.k}, "
                                f"fields={self.fields}, exhaustive={self.exhaustive})")
                
                USING_SDK_VERSION = "Compatibility"

# Also implement VectorSearch for latest API version
class VectorizedQuery:
    """Compatibility implementation of VectorizedQuery for 2023-07-01-Preview API."""
    def __init__(self, vector, k_nearest_neighbors, fields):
        self.vector = vector
        self.k_nearest_neighbors = k_nearest_neighbors
        self.fields = fields

# Convert numpy arrays to lists if numpy is available
try:
    import numpy as np
    
    original_init = Vector.__init__
    
    def patched_init(self, value, **kwargs):
        """Patch Vector.__init__ to convert numpy arrays to lists."""
        if isinstance(value, np.ndarray):
            value = value.tolist()
        return original_init(self, value, **kwargs)
    
    Vector.__init__ = patched_init
except ImportError:
    pass  # numpy not available, no patching needed

logger.info(f"Using Azure Search Vector class from: {USING_SDK_VERSION}")