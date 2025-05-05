// frontend/src/components/ProtectedRoute.js
import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useEntraAuth } from '../hooks/useEntraAuth';
import { InteractionStatus } from '@azure/msal-browser';

/**
 * A wrapper component for routes that require authentication
 * Redirects to login if user is not authenticated
 */
const ProtectedRoute = ({ children }) => {
  const { user, loading, isAuthenticated, isTokenValid, msalInstance, configError } = useEntraAuth();
  const [isChecking, setIsChecking] = useState(true);
  const [isValid, setIsValid] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const checkAuth = async () => {
      // If we have a config error, we can't authenticate
      if (configError) {
        setIsValid(false);
        setIsChecking(false);
        return;
      }
      
      // If MSAL is in the middle of a redirect, wait for it to complete
      if (msalInstance && msalInstance.getInteractionStatus) {
        const status = msalInstance.getInteractionStatus();
        if (status === InteractionStatus.Redirect) {
          return;
        }
      }
      
      // Check if we have a valid token first
      const tokenValid = isTokenValid();
      
      // If no valid token, we can immediately redirect
      if (!tokenValid) {
        setIsValid(false);
        setIsChecking(false);
        return;
      }
      
      // If we have a token but auth is still loading, wait for it
      if (loading) {
        return;
      }
      
      // Auth loading complete, check if we have a user
      setIsValid(isAuthenticated);
      setIsChecking(false);
    };
    
    checkAuth();
  }, [user, loading, isAuthenticated, isTokenValid, msalInstance, configError]);

  // Store the current location for redirect after login
  useEffect(() => {
    if (!isValid && !isChecking && !loading) {
      // Store the current path for redirect after login
      sessionStorage.setItem('redirectTo', location.pathname);
    }
  }, [isValid, isChecking, loading, location.pathname]);

  // Show loading state while checking
  if (loading || isChecking) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="flex flex-col items-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-600">Verifying authentication...</p>
        </div>
      </div>
    );
  }
  
  // If configuration error, redirect to login with error
  if (configError) {
    return <Navigate to="/login" state={{ error: configError }} replace />;
  }
  
  // If not authenticated, redirect to login
  if (!isValid) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  // If authenticated, render the children
  return children;
};

export default ProtectedRoute;