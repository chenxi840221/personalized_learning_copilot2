// Update your frontend/src/context/AuthContext.js file if needed
import React, { createContext, useState, useEffect } from 'react';
import { login, register, getCurrentUser, logout } from '../services/auth';

// Create the Auth Context
export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check if user is already logged in on initial load
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // Get token from local storage
        const token = localStorage.getItem('token');
        
        if (token) {
          // Get current user if token exists
          const userData = await getCurrentUser();
          setUser(userData);
        }
      } catch (err) {
        console.error('Auth check failed:', err);
        // Clear any invalid tokens
        localStorage.removeItem('token');
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  // Login function
  const handleLogin = async (username, password) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await login(username, password);
      
      // Get user data
      const userData = await getCurrentUser();
      setUser(userData);
      
      return userData;
    } catch (err) {
      setError(err.message || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const handleRegister = async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
      await register(userData);
      // After registration, log the user in
      return await handleLogin(userData.username, userData.password);
    } catch (err) {
      setError(err.message || 'Registration failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const handleLogout = () => {
    // Remove token from local storage
    localStorage.removeItem('token');
    // Clear user state
    setUser(null);
    // Call logout service
    logout();
  };

  // Context value
  const value = {
    user,
    loading,
    error,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};