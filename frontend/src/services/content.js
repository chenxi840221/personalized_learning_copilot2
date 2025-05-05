// frontend/src/services/content.js
import { api } from './api';

/**
 * Get all content with optional filters
 * @param {string|null} subject - Optional subject filter
 * @param {string|null} contentType - Optional content type filter
 * @param {string|null} difficulty - Optional difficulty filter
 * @param {number|null} gradeLevel - Optional grade level filter
 * @returns {Promise<Array>} Array of content items
 */
export const getContent = async (subject = null, contentType = null, difficulty = null, gradeLevel = null, page = 1, limit = 100) => {
  try {
    console.log(`🔍 Fetching content with filters - Subject: ${subject}, Type: ${contentType}, Page: ${page}`);
    
    // Build query parameters
    const params = {
      page,
      limit
    };
    
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    if (contentType) params.content_type = contentType;
    if (difficulty) params.difficulty = difficulty;
    if (gradeLevel) params.grade_level = gradeLevel;
    
    // Make API request
    const result = await api.get('/content', params);
    console.log(`📚 Received ${result?.length || 0} content items from API (page ${page})`);
    return result;
  } catch (error) {
    console.error('❌ Failed to fetch content:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.status || 'N/A',
      data: error.data || 'N/A'
    });
    throw error;
  }
};

/**
 * Get recommended content based on user profile
 * @param {string|null} subject - Optional subject filter
 * @returns {Promise<Array>} Array of recommended content items
 */
export const getRecommendations = async (subject = null, page = 1, limit = 100) => {
  try {
    console.log(`🔍 Fetching personalized recommendations${subject ? ` for ${subject}` : ''} (page ${page})`);
    
    // Build query parameters
    const params = {
      page,
      limit
    };
    
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    
    try {
      // First try the recommendations endpoint
      const result = await api.get('/content/recommendations', params);
      console.log(`📚 Received ${result?.length || 0} recommended items from API (page ${page})`);
      return result;
    } catch (recommendationError) {
      // If recommendations endpoint fails, fallback to main content endpoint
      console.log('⚠️ Recommendations endpoint failed, falling back to content endpoint');
      console.error(recommendationError);
      
      // Fallback to the regular content endpoint
      const fallbackResult = await api.get('/content', params);
      console.log(`📚 Received ${fallbackResult?.length || 0} content items from fallback API`);
      return fallbackResult;
    }
  } catch (error) {
    console.error('❌ Failed to fetch recommendations:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.status || 'N/A',
      data: error.data || 'N/A'
    });
    
    // Return empty array instead of throwing to provide graceful degradation
    return [];
  }
};

/**
 * Search for content using text and vector search
 * @param {string} query - Search query
 * @param {string|null} subject - Optional subject filter
 * @param {string|null} contentType - Optional content type filter
 * @returns {Promise<Array>} Array of content items matching the search
 */
export const searchContent = async (query, subject = null, contentType = null, page = 1, limit = 100) => {
  try {
    console.log(`🔍 Searching for content with query: "${query}"${subject ? `, subject: ${subject}` : ''}${contentType ? `, type: ${contentType}` : ''} (page ${page})`);
    
    // Build query parameters
    const params = { 
      query,
      page,
      limit
    };
    
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    if (contentType) params.content_type = contentType;
    
    // Make API request using GET as defined in the backend
    const result = await api.get('/content/search', params);
    console.log(`🔎 Found ${result?.length || 0} search results (page ${page})`);
    return result;
  } catch (error) {
    console.error('❌ Failed to search content:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.status || 'N/A',
      data: error.data || 'N/A'
    });
    
    // Return empty array instead of throwing to provide graceful degradation
    return [];
  }
};

/**
 * Get content by ID
 * @param {string} contentId - Content ID
 * @returns {Promise<Object>} Content item 
 */
export const getContentById = async (contentId) => {
  try {
    console.log(`🔍 Fetching content with ID: ${contentId}`);
    
    // Make API request
    const result = await api.get(`/content/${contentId}`);
    console.log(`📚 Received content item from API:`, result);
    return result;
  } catch (error) {
    console.error(`❌ Failed to fetch content with ID ${contentId}:`, error);
    console.error('Error details:', {
      message: error.message,
      status: error.status || 'N/A',
      data: error.data || 'N/A'
    });
    throw error;
  }
};

/**
 * Get learning plans for current user
 * @param {string|null} subject - Optional subject filter
 * @returns {Promise<Array>} Array of learning plans
 */
export const getLearningPlans = async (subject = null) => {
  try {
    // Build query parameters
    const params = {};
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    
    // Make API request
    return await api.get('/learning-plans/', params);
  } catch (error) {
    console.error('Failed to fetch learning plans:', error);
    throw error;
  }
};

/**
 * Create a new learning plan
 * @param {string} subject - Subject for the learning plan
 * @param {string} [learning_period] - Learning period (one_week, two_weeks, one_month, two_months, school_term)
 * @returns {Promise<Object>} Created learning plan
 */
export const createLearningPlan = async (subject, learning_period = 'one_month') => {
  try {
    return await api.post('/learning-plans/', { subject, learning_period });
  } catch (error) {
    console.error('Failed to create learning plan:', error);
    throw error;
  }
};

/**
 * Create a new learning plan using student profile
 * @param {Object} planData - Learning plan data
 * @param {string} planData.student_profile_id - ID of the student profile
 * @param {string} [planData.subject] - Subject for a single-subject plan
 * @param {number} [planData.daily_minutes] - Daily study time in minutes
 * @param {string} [planData.type] - Plan type ('balanced' or 'focused')
 * @param {string} [planData.learning_period] - Learning period (one_week, two_weeks, one_month, two_months, school_term)
 * @returns {Promise<Object>} Created learning plan
 */
export const createProfileBasedPlan = async (planData) => {
  try {
    console.log(`🔍 Creating profile-based learning plan with data:`, planData);
    return await api.post('/learning-plans/profile-based', planData);
  } catch (error) {
    console.error('Failed to create profile-based learning plan:', error);
    throw error;
  }
};

/**
 * Update learning activity status
 * @param {string} planId - Learning plan ID
 * @param {string} activityId - Activity ID
 * @param {string} status - New status (not_started, in_progress, completed)
 * @param {string|null} completedAt - Optional ISO date string when the activity was completed
 * @returns {Promise<Object>} Update result
 */
export const updateActivityStatus = async (planId, activityId, status, completedAt = null) => {
  try {
    return await api.put(`/learning-plans/${planId}/activities/${activityId}`, {
      status,
      completed_at: completedAt
    });
  } catch (error) {
    console.error('Failed to update activity status:', error);
    throw error;
  }
};

/**
 * Delete a learning plan
 * @param {string} planId - Learning plan ID to delete
 * @returns {Promise<Object>} Delete result
 */
export const deleteLearningPlan = async (planId) => {
  try {
    return await api.delete(`/learning-plans/${planId}`);
  } catch (error) {
    console.error('Failed to delete learning plan:', error);
    throw error;
  }
};

/**
 * Update a learning plan
 * @param {string} planId - Learning plan ID
 * @param {Object} planData - Updated plan data
 * @returns {Promise<Object>} Updated learning plan
 */
export const updateLearningPlan = async (planId, planData) => {
  try {
    return await api.put(`/learning-plans/${planId}`, planData);
  } catch (error) {
    console.error('Failed to update learning plan:', error);
    throw error;
  }
};

/**
 * Export a learning plan
 * @param {string} planId - Learning plan ID
 * @param {string} format - Export format (json, html, pdf)
 * @returns {Promise<Object>} Exported learning plan
 */
export const exportLearningPlan = async (planId, format = 'json') => {
  try {
    return await api.get(`/learning-plans/${planId}/export`, { format });
  } catch (error) {
    console.error('Failed to export learning plan:', error);
    throw error;
  }
};

/**
 * Get AI-generated personalized recommendations
 * @param {string|null} subject - Optional subject filter
 * @returns {Promise<Array>} Array of AI-recommended content items
 */
export const getAIRecommendations = async (subject = null) => {
  try {
    // Build query parameters
    const params = {};
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    
    // Make API request to AI endpoint
    return await api.get('/ai/personalized-recommendations', params);
  } catch (error) {
    console.error('Failed to fetch AI recommendations:', error);
    // Fall back to regular recommendations
    return await getRecommendations(subject);
  }
};

/**
 * Create an AI-generated learning plan
 * @param {Object} planData - Learning plan data
 * @param {string} [planData.subject] - Subject for a single-subject plan
 * @param {string} [planData.student_profile_id] - ID of the student profile
 * @param {number} [planData.daily_minutes] - Daily study time in minutes
 * @param {string} [planData.type] - Plan type ('balanced' or 'focused')
 * @param {string} [planData.learning_period] - Learning period (one_week, two_weeks, one_month, two_months, school_term)
 * @returns {Promise<Object>} Created learning plan
 */
export const createAILearningPlan = async (planData) => {
  try {
    // If this is a profile-based plan
    if (planData.student_profile_id) {
      return await createProfileBasedPlan(planData);
    }
    
    // Legacy subject-only plan
    if (typeof planData === 'string' || (planData && planData.subject && !planData.student_profile_id)) {
      const subject = typeof planData === 'string' ? planData : planData.subject;
      const learning_period = typeof planData === 'string' ? 'one_month' : (planData.learning_period || 'one_month');
      return await api.post('/ai/learning-plan', { subject, learning_period });
    }
    
    throw new Error('Invalid plan data - must provide either subject or student_profile_id');
  } catch (error) {
    console.error('Failed to create AI learning plan:', error);
    
    // Fall back to regular plan creation only for subject-based plans
    if (typeof planData === 'string') {
      return await createLearningPlan(planData);
    } else if (planData.subject && !planData.student_profile_id) {
      return await createLearningPlan(planData.subject, planData.learning_period || 'one_month');
    }
    
    throw error;
  }
};