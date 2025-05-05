// frontend/src/components/Login.js
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useEntraAuth } from '../hooks/useEntraAuth';

const Login = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [loginFallback, setLoginFallback] = useState(false);
  
  const { 
    user, 
    loading, 
    error: authError, 
    configError,
    login, 
    isAuthenticated, 
    msalInitialized 
  } = useEntraAuth();
  
  const navigate = useNavigate();
  const location = useLocation();
  
  // Check for environment variables
  const checkEnvVars = () => {
    const missing = [];
    
    if (!process.env.REACT_APP_CLIENT_ID || process.env.REACT_APP_CLIENT_ID === 'your-client-id-here') {
      missing.push('Client ID (REACT_APP_CLIENT_ID)');
    }
    
    if (!process.env.REACT_APP_TENANT_ID || process.env.REACT_APP_TENANT_ID === 'your-tenant-id-here') {
      missing.push('Tenant ID (REACT_APP_TENANT_ID)');
    }
    
    return missing.length > 0 ? missing : null;
  };
  
  const missingEnvVars = checkEnvVars();
  
  // Get redirect URL from location state
  const from = location.state?.from?.pathname || '/dashboard';
  
  // Store the redirect path for after authentication
  useEffect(() => {
    if (from && from !== '/login') {
      sessionStorage.setItem('redirectTo', from);
    }
  }, [from]);
  
  // Display auth errors from context
  useEffect(() => {
    if (authError) {
      setError(authError);
      setIsLoading(false);
    }
  }, [authError]);
  
  // If already authenticated, redirect to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);
  
  // Handle login click
  const handleLogin = async () => {
    if (!msalInitialized) {
      setError('Authentication system is still initializing. Please try again in a moment.');
      return;
    }
    
    try {
      setIsLoading(true);
      setError('');
      
      // Start Entra ID login flow
      await login();
      
      // Set a timeout to show fallback option if login doesn't work
      setTimeout(() => {
        setLoginFallback(true);
      }, 10000);
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message || 'Failed to login. Please try again.');
      setIsLoading(false);
    }
  };
  
  // Show configuration error
  if (configError || missingEnvVars) {
    return (
      <div className="flex justify-center items-center min-h-[80vh]">
        <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
          <h2 className="text-2xl font-bold text-center text-red-600 mb-6">
            Configuration Error
          </h2>
          
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {configError && <p className="mb-2">{configError}</p>}
            
            {missingEnvVars && (
              <>
                <p className="font-medium">Missing environment variables:</p>
                <ul className="list-disc pl-5 mt-1">
                  {missingEnvVars.map(item => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            )}
            
            <p className="mt-3 text-sm">
              Please check your .env.local file and ensure it has the following variables:
            </p>
            <pre className="mt-2 bg-red-50 p-2 rounded text-xs overflow-x-auto">
              REACT_APP_API_URL=http://localhost:8000<br/>
              REACT_APP_CLIENT_ID=your-actual-client-id<br/>
              REACT_APP_TENANT_ID=your-actual-tenant-id<br/>
              REACT_APP_API_SCOPE=api://your-actual-client-id/user_impersonation
            </pre>
            <p className="mt-3 text-sm">
              After updating the file, restart the development server.
            </p>
          </div>
          
          <button
            onClick={() => window.location.reload()}
            className="w-full bg-blue-600 text-white font-bold py-3 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
          >
            Refresh page
          </button>
        </div>
      </div>
    );
  }
  
  // Show initialization message
  if (loading && !msalInitialized) {
    return (
      <div className="flex justify-center items-center min-h-[80vh]">
        <div className="flex flex-col items-center bg-white p-8 rounded-lg shadow-md w-full max-w-md">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-600">Initializing authentication system...</p>
        </div>
      </div>
    );
  }
  
  // If still checking authentication status, show loading
  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[80vh]">
        <div className="flex flex-col items-center bg-white p-8 rounded-lg shadow-md w-full max-w-md">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-600">Checking authentication status...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex justify-center items-center min-h-[80vh]">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold text-center text-blue-600 mb-6">
          Login to Learning Co-pilot
        </h2>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <div className="space-y-6">
          <div className="flex flex-col space-y-2">
            <button
              onClick={handleLogin}
              className="w-full bg-[#0078d4] text-white font-bold py-3 px-4 rounded-md hover:bg-[#106ebe] focus:outline-none focus:ring-2 focus:ring-[#0078d4] focus:ring-opacity-50 disabled:opacity-50 flex items-center justify-center"
              disabled={isLoading || !msalInitialized}
            >
              {isLoading ? (
                <>
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></span>
                  Signing in...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 15a7 7 0 110-14 7 7 0 010 14z" />
                  </svg>
                  Sign in with Microsoft
                </>
              )}
            </button>
          </div>
          
          <div className="text-center text-sm text-gray-600">
            <p>
              This application uses Entra ID (formerly Azure AD) for authentication.
            </p>
            <p className="mt-2">
              You will be redirected to the Microsoft login page.
            </p>
            
            {!msalInitialized && !loading && (
              <p className="mt-2 text-red-600">
                Authentication system is not initialized. Check your configuration.
              </p>
            )}
          </div>
          
          {/* Show fallback option if login is taking too long */}
          {isLoading && loginFallback && (
            <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-sm text-yellow-800 mb-2">
                <strong>Taking too long?</strong> There might be an issue with the Microsoft login service.
              </p>
              <p className="text-sm text-yellow-800 mb-2">
                Make sure your browser isn't blocking pop-ups.
              </p>
              <button
                onClick={() => window.location.reload()}
                className="w-full mt-2 bg-yellow-100 text-yellow-800 border border-yellow-300 py-2 px-4 rounded-md text-sm hover:bg-yellow-200"
              >
                Refresh the page
              </button>
            </div>
          )}
        </div>
        
        {/* Debug info section */}
        <div className="mt-8 pt-4 border-t border-gray-200">
          <details className="text-xs text-gray-500">
            <summary className="cursor-pointer">Debug Info</summary>
            <div className="mt-2 p-2 bg-gray-50 rounded text-left">
              <p>Environment: {process.env.NODE_ENV}</p>
              <p>Client ID configured: {process.env.REACT_APP_CLIENT_ID ? 'Yes' : 'No'}</p>
              <p>Tenant ID configured: {process.env.REACT_APP_TENANT_ID ? 'Yes' : 'No'}</p>
              <p>API Scope configured: {process.env.REACT_APP_API_SCOPE ? 'Yes' : 'No'}</p>
              <p>MSAL Initialized: {msalInitialized ? 'Yes' : 'No'}</p>
              <p>Redirect URI: {window.location.origin + '/auth/callback'}</p>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
};

export default Login;