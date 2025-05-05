// Helper Utilities (helpers.js)
// ./personalized_learning_copilot/frontend/src/utils/helpers.js

/**
 * Format a date to a readable string
 * @param {string|Date} dateString - Date to format
 * @param {boolean} includeTime - Whether to include time in the formatted output
 * @returns {string} Formatted date string
 */
export const formatDate = (dateString, includeTime = false) => {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    
    // Check if date is valid
    if (isNaN(date.getTime())) return 'Invalid date';
    
    const options = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    };
    
    if (includeTime) {
      options.hour = '2-digit';
      options.minute = '2-digit';
    }
    
    return date.toLocaleDateString(undefined, options);
  };
  
  /**
   * Format a duration in minutes to a readable string
   * @param {number} minutes - Duration in minutes
   * @returns {string} Formatted duration string
   */
  export const formatDuration = (minutes) => {
    if (!minutes && minutes !== 0) return 'N/A';
    
    if (minutes < 60) {
      return `${minutes} min`;
    }
    
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    
    if (mins === 0) {
      return `${hours} hr`;
    }
    
    return `${hours} hr ${mins} min`;
  };
  
  /**
   * Truncate a string to a maximum length with ellipsis
   * @param {string} str - String to truncate
   * @param {number} maxLength - Maximum length
   * @returns {string} Truncated string
   */
  export const truncateString = (str, maxLength = 100) => {
    if (!str) return '';
    
    if (str.length <= maxLength) return str;
    
    return str.substring(0, maxLength) + '...';
  };
  
  /**
   * Capitalize the first letter of each word in a string
   * @param {string} str - String to capitalize
   * @returns {string} Capitalized string
   */
  export const capitalizeWords = (str) => {
    if (!str) return '';
    
    return str
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };
  
  /**
   * Format a string from snake_case or kebab-case to readable text
   * @param {string} str - String to format
   * @returns {string} Formatted string
   */
  export const formatFromCase = (str) => {
    if (!str) return '';
    
    // Replace underscores and hyphens with spaces
    const spacedStr = str.replace(/[_-]/g, ' ');
    
    // Capitalize each word
    return capitalizeWords(spacedStr);
  };
  
  /**
   * Calculate percentage of completed items
   * @param {number} completed - Number of completed items
   * @param {number} total - Total number of items
   * @returns {number} Percentage (0-100)
   */
  export const calculatePercentage = (completed, total) => {
    if (!total || total === 0) return 0;
    
    const percentage = (completed / total) * 100;
    return Math.round(percentage);
  };
  
  /**
   * Group array items by a specific property
   * @param {Array} array - Array to group
   * @param {string} key - Property to group by
   * @returns {Object} Grouped object
   */
  export const groupBy = (array, key) => {
    if (!array || !Array.isArray(array)) return {};
    
    return array.reduce((result, item) => {
      const groupKey = item[key];
      
      if (!result[groupKey]) {
        result[groupKey] = [];
      }
      
      result[groupKey].push(item);
      return result;
    }, {});
  };
  
  /**
   * Sort array by a specific property
   * @param {Array} array - Array to sort
   * @param {string} key - Property to sort by
   * @param {boolean} ascending - Sort in ascending order
   * @returns {Array} Sorted array
   */
  export const sortBy = (array, key, ascending = true) => {
    if (!array || !Array.isArray(array)) return [];
    
    const sortedArray = [...array].sort((a, b) => {
      if (a[key] < b[key]) return ascending ? -1 : 1;
      if (a[key] > b[key]) return ascending ? 1 : -1;
      return 0;
    });
    
    return sortedArray;
  };
  
  /**
   * Filter array by search term across multiple properties
   * @param {Array} array - Array to filter
   * @param {string} searchTerm - Term to search for
   * @param {Array} keys - Properties to search in
   * @returns {Array} Filtered array
   */
  export const filterBySearch = (array, searchTerm, keys) => {
    if (!array || !Array.isArray(array) || !searchTerm) return array;
    
    const term = searchTerm.toLowerCase();
    
    return array.filter(item => {
      return keys.some(key => {
        const value = item[key];
        
        if (typeof value === 'string') {
          return value.toLowerCase().includes(term);
        }
        
        return false;
      });
    });
  };
  
  /**
   * Get status color class based on status string
   * @param {string} status - Status string
   * @returns {string} CSS class for status color
   */
  export const getStatusColorClass = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'not_started':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };
  
  /**
   * Format a status string to a readable format
   * @param {string} status - Status string
   * @returns {string} Formatted status string
   */
  export const formatStatus = (status) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'in_progress':
        return 'In Progress';
      case 'not_started':
        return 'Not Started';
      default:
        return status ? formatFromCase(status) : 'Unknown';
    }
  };