// frontend/src/components/AuthCallback.js
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useEntraAuth } from '../hooks/useEntraAuth';

/**
 * Component to handle Entra ID authentication callback
 * This receives the auth code from Microsoft login and exchanges it for a token
 */
const AuthCallback = () => {
  const [status, setStatus] = useState('Processing authentication...');
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { msalInstance, error: authError } = useEntraAuth();
  
  useEffect(() => {
    // Parse error from URL if present
    const urlParams = new URLSearchParams(window.location.search);
    const errorParam = urlParams.get('error');
    const errorDescription = urlParams.get('error_description');
    
    if (errorParam) {
      setError(`${errorParam}: ${errorDescription || 'Unknown error'}`);
      setStatus('Authentication failed');
      return;
    }
    
    // Authentication is handled by MSAL directly
    // We just need to wait for the redirect handling to complete
    if (msalInstance) {
      // Redirect to dashboard or intended location after processing
      const redirectTo = sessionStorage.getItem('redirectTo') || '/dashboard';
      sessionStorage.removeItem('redirectTo');
      
      // Add a short delay to allow MSAL to complete processing
      setTimeout(() => {
        navigate(redirectTo, { replace: true });
      }, 500);
    } else {
      setStatus('Initializing authentication...');
    }
  }, [msalInstance, navigate]);
  
  // Display auth errors from context
  useEffect(() => {
    if (authError) {
      setError(authError);
      setStatus('Authentication failed');
    }
  }, [authError]);
  
  return (
    <div className="flex justify-center items-center h-screen">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md text-center">
        {error ? (
          <>
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              <p className="font-bold">Authentication Error</p>
              <p>{error}</p>
            </div>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700"
            >
              Return to Login
            </button>
          </>
        ) : (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">Completing Login</h2>
            <p className="text-gray-600 mb-4">{status}</p>
            <p className="text-sm text-gray-500">You will be redirected automatically...</p>
          </>
        )}
      </div>
    </div>
  );
};

export default AuthCallback;