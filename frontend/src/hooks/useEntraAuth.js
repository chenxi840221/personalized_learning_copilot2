// frontend/src/hooks/useEntraAuth.js
import { useContext } from 'react';
import { EntraAuthContext } from '../context/EntraAuthContext';

/**
 * Custom hook to access the Entra ID authentication context
 * @returns {Object} Authentication context
 */
export const useEntraAuth = () => {
  const context = useContext(EntraAuthContext);
  
  if (!context) {
    throw new Error('useEntraAuth must be used within an EntraAuthProvider');
  }
  
  return context;
};

export default useEntraAuth;