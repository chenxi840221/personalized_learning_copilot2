// frontend/src/services/auth.js
import { api, apiClient } from './api';

// Login function
export const login = async (username, password) => {
  try {
    // Use URLSearchParams to format data as form data
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await apiClient.post('/auth/token', formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    
    // Store token in local storage
    localStorage.setItem('token', response.data.access_token);
    
    return response.data;
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to login';
    throw new Error(message);
  }
};

// Register function
export const register = async (userData) => {
  try {
    // Convert learning_style enum format if needed
    if (userData.learning_style) {
      // Our backend expects simple strings, not objects
      userData.learning_style = userData.learning_style.value || userData.learning_style;
    }
    
    const response = await api.post('/auth/register', userData);
    return response;
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to register';
    throw new Error(message);
  }
};

// Get current user
export const getCurrentUser = async () => {
  try {
    const response = await api.get('/users/me/');
    return response;
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to get user data';
    throw new Error(message);
  }
};

// Logout (client-side only)
export const logout = () => {
  // Remove token from local storage
  localStorage.removeItem('token');
};