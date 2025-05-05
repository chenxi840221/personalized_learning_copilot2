// frontend/src/context/EntraAuthContext.js
import React, { createContext, useState, useEffect, useCallback } from 'react';
import { PublicClientApplication, InteractionRequiredAuthError } from '@azure/msal-browser';
import axios from 'axios';
import { apiClient } from '../services/api';

// Create the Auth Context
export const EntraAuthContext = createContext();

// MSAL configuration for Entra ID with validation
const getMsalConfig = () => {
  const clientId = process.env.REACT_APP_CLIENT_ID;
  const tenantId = process.env.REACT_APP_TENANT_ID;
  
  if (!clientId || clientId === 'your-client-id-here') {
    console.error('Missing or invalid client ID in environment variables');
    return null;
  }
  
  if (!tenantId || tenantId === 'your-tenant-id-here') {
    console.error('Missing or invalid tenant ID in environment variables');
    return null;
  }
  
  return {
    auth: {
      clientId,
      authority: `https://login.microsoftonline.com/${tenantId}`,
      redirectUri: window.location.origin + '/auth/callback',
      navigateToLoginRequestUrl: true,
    },
    cache: {
      cacheLocation: 'sessionStorage',
      storeAuthStateInCookie: false
    }
  };
};

const msalConfig = getMsalConfig();

// Authentication scopes - UPDATED to use Microsoft Graph scopes instead of custom API
const loginRequest = {
  scopes: ['User.Read']
};

const apiRequest = {
  scopes: ['User.Read']  // Using standard Microsoft Graph scope instead of custom API
};

export const EntraAuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [msalInstance, setMsalInstance] = useState(null);
  const [msalInitialized, setMsalInitialized] = useState(false);
  const [configError, setConfigError] = useState(null);
  
  // Initialize MSAL instance
  useEffect(() => {
    const initializeMsal = async () => {
      try {
        if (!msalConfig) {
          const errorMsg = 'Missing or invalid MSAL configuration. Check environment variables.';
          console.error(errorMsg);
          setConfigError(errorMsg);
          setLoading(false);
          return;
        }
        
        console.log('Initializing MSAL with config:', { 
          clientId: msalConfig.auth.clientId,
          authority: msalConfig.auth.authority,
          redirectUri: msalConfig.auth.redirectUri 
        });
        
        const msalApp = new PublicClientApplication(msalConfig);
        
        // Important: Explicitly call initialize and await it
        await msalApp.initialize();
        console.log('MSAL initialized successfully');
        
        setMsalInstance(msalApp);
        setMsalInitialized(true);
        
        // Handle redirect response after initialization
        try {
          const response = await msalApp.handleRedirectPromise();
          console.log('MSAL redirect response:', response ? 'Success' : 'No response');
          
          if (response) {
            // Handle successful authentication
            await handleResponse(response, msalApp);
          } else {
            // Check if user is already signed in
            const accounts = msalApp.getAllAccounts();
            console.log('MSAL accounts:', accounts.length);
            
            if (accounts.length > 0) {
              msalApp.setActiveAccount(accounts[0]);
              await getUserInfo(msalApp);
            } else {
              setLoading(false);
            }
          }
        } catch (redirectErr) {
          console.error('Error handling redirect:', redirectErr);
          setError(redirectErr.message || 'Failed to process authentication response');
          setLoading(false);
        }
      } catch (err) {
        console.error('Error initializing MSAL:', err);
        setError(err.message || 'Failed to initialize authentication');
        setLoading(false);
      }
    };
    
    initializeMsal();
  }, []);
  
  // Handle authentication response
  const handleResponse = useCallback(async (response, msalApp) => {
    if (response && response.account) {
      // Set active account
      msalApp.setActiveAccount(response.account);
      
      // Get user info
      await getUserInfo(msalApp || msalInstance);
    }
  }, []);
  
  // Get user information from token and profile API
  const getUserInfo = useCallback(async (msalApp) => {
    if (!msalApp) {
      console.error('MSAL instance not available');
      return;
    }
    
    try {
      setLoading(true);
      
      // Get access token for API
      const tokenResponse = await msalApp.acquireTokenSilent(apiRequest);
      console.log('Token acquired successfully');
      
      // Set authorization header for API requests
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${tokenResponse.accessToken}`;
      
      try {
        // Get user profile from API
        const userProfile = await apiClient.get('/auth/profile');
        console.log('User profile retrieved');
        
        // Set user info
        setUser({
          ...userProfile.data,
          accessToken: tokenResponse.accessToken
        });
      } catch (profileError) {
        console.error('Error getting user profile from API:', profileError);
        // Fall back to using the token claims
        const account = tokenResponse.account;
        const idTokenClaims = account.idTokenClaims || {};
        
        console.log('Using ID token claims for user info:', idTokenClaims);
        
        setUser({
          id: account.homeAccountId,
          username: account.username,
          email: idTokenClaims.email || account.username,
          name: account.name,
          given_name: idTokenClaims.given_name,
          family_name: idTokenClaims.family_name,
          accessToken: tokenResponse.accessToken
        });
      }
      
      setLoading(false);
    } catch (err) {
      if (err instanceof InteractionRequiredAuthError) {
        // User needs to login again
        console.log('Interaction required, redirecting to login');
        msalApp.acquireTokenRedirect(apiRequest);
      } else {
        console.error('Error getting user info:', err);
        setError(err.message || 'Failed to get user information');
        setLoading(false);
      }
    }
  }, []);
  
  // Login function
  const login = useCallback(async () => {
    if (!msalInstance || !msalInitialized) {
      console.error('MSAL instance not initialized');
      setError('Authentication system not initialized. Please try again later.');
      return;
    }
    
    try {
      console.log('Starting login flow...');
      
      // Try popup login for better error visibility in development
      if (process.env.NODE_ENV === 'development') {
        console.log('Using popup for login in development');
        const response = await msalInstance.loginPopup(loginRequest);
        console.log('Login popup completed', response);
        
        if (response && response.account) {
          msalInstance.setActiveAccount(response.account);
          await getUserInfo(msalInstance);
        }
      } else {
        // Use redirect flow in production
        await msalInstance.loginRedirect(loginRequest);
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message || 'Failed to login. Please try again.');
    }
  }, [msalInstance, msalInitialized, getUserInfo]);
  
  // Logout function
  const logout = useCallback(() => {
    if (!msalInstance || !msalInitialized) {
      console.error('MSAL instance not initialized');
      return;
    }
    
    try {
      // Logout user
      const logoutRequest = {
        account: msalInstance.getActiveAccount(),
        postLogoutRedirectUri: window.location.origin
      };
      
      // Clear user state
      setUser(null);
      
      // Clear auth header
      delete apiClient.defaults.headers.common['Authorization'];
      
      // Redirect to logout
      msalInstance.logoutRedirect(logoutRequest);
    } catch (err) {
      console.error('Logout error:', err);
    }
  }, [msalInstance, msalInitialized]);
  
  // Get access token for API calls
  const getAccessToken = useCallback(async () => {
    if (!msalInstance || !msalInitialized) return null;
    
    try {
      // Try silent token acquisition first
      const tokenResponse = await msalInstance.acquireTokenSilent(apiRequest);
      return tokenResponse.accessToken;
    } catch (err) {
      if (err instanceof InteractionRequiredAuthError) {
        // User needs to login again
        console.log('Interaction required, redirecting to login');
        await msalInstance.acquireTokenRedirect(apiRequest);
        return null;
      }
      console.error('Error getting access token:', err);
      return null;
    }
  }, [msalInstance, msalInitialized]);
  
  // Check if user is authenticated
  const isAuthenticated = !!user;
  
  // Check if token is valid
  const isTokenValid = useCallback(() => {
    if (!user || !user.accessToken) return false;
    
    // Get token parts
    const tokenParts = user.accessToken.split('.');
    if (tokenParts.length !== 3) return false;
    
    try {
      // Decode token payload
      const payload = JSON.parse(atob(tokenParts[1]));
      
      // Check if token is expired
      const now = Math.floor(Date.now() / 1000);
      return payload.exp > now;
    } catch (err) {
      console.error('Error validating token:', err);
      return false;
    }
  }, [user]);
  
  // Context value
  const value = {
    user,
    loading,
    error,
    configError,
    login,
    logout,
    getAccessToken,
    isAuthenticated,
    isTokenValid,
    msalInstance,
    msalInitialized
  };

  return (
    <EntraAuthContext.Provider value={value}>
      {children}
    </EntraAuthContext.Provider>
  );
};

export default EntraAuthContext;