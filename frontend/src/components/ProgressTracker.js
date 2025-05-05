import React, { useState, useEffect } from 'react';
import { getLearningPlans } from '../services/content';

const ProgressTracker = () => {
  const [learningPlans, setLearningPlans] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({
    total: 0,
    completed: 0,
    inProgress: 0,
    subjects: {}
  });

  // Fetch learning plans on component mount
  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setIsLoading(true);
        const plans = await getLearningPlans();
        setLearningPlans(plans);
        calculateStats(plans);
      } catch (err) {
        console.error('Error fetching learning plans:', err);
        setError('Failed to load learning plans');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPlans();
  }, []);

  // Calculate statistics from learning plans
  const calculateStats = (plans) => {
    const total = plans.length;
    const completed = plans.filter(plan => plan.status === 'completed').length;
    const inProgress = plans.filter(plan => plan.status === 'in_progress').length;
    
    // Calculate subject-specific stats
    const subjects = {};
    
    plans.forEach(plan => {
      const subject = plan.subject;
      
      if (!subjects[subject]) {
        subjects[subject] = {
          total: 0,
          completed: 0,
          inProgress: 0,
          percentage: 0
        };
      }
      
      subjects[subject].total += 1;
      
      if (plan.status === 'completed') {
        subjects[subject].completed += 1;
      } else if (plan.status === 'in_progress') {
        subjects[subject].inProgress += 1;
      }
      
      // Calculate completion percentage for each subject
      subjects[subject].percentage = Math.round(
        (subjects[subject].completed / subjects[subject].total) * 100
      );
    });
    
    setStats({
      total,
      completed,
      inProgress,
      subjects
    });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-48">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
        {error}
      </div>
    );
  }

  // Get overall progress percentage
  const overallProgress = stats.total > 0 
    ? Math.round((stats.completed / stats.total) * 100) 
    : 0;

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-800 mb-6">Your Learning Progress</h2>

      {/* Overall Progress */}
      <div className="mb-8">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">Overall Progress</span>
          <span className="text-sm font-medium text-gray-700">{overallProgress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div 
            className="bg-blue-600 h-2.5 rounded-full" 
            style={{ width: `${overallProgress}%` }}
          ></div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
          <p className="text-sm text-blue-700 font-medium">Total Plans</p>
          <p className="text-2xl font-bold text-blue-800">{stats.total}</p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg border border-green-100">
          <p className="text-sm text-green-700 font-medium">Completed</p>
          <p className="text-2xl font-bold text-green-800">{stats.completed}</p>
        </div>
        <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-100">
          <p className="text-sm text-yellow-700 font-medium">In Progress</p>
          <p className="text-2xl font-bold text-yellow-800">{stats.inProgress}</p>
        </div>
      </div>

      {/* Progress by Subject */}
      {Object.keys(stats.subjects).length > 0 && (
        <div>
          <h3 className="text-lg font-medium text-gray-800 mb-4">Progress by Subject</h3>
          
          <div className="space-y-4">
            {Object.entries(stats.subjects).map(([subject, subjectStats]) => (
              <div key={subject} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium text-gray-800">{subject}</span>
                  <span className="text-sm font-medium text-gray-700">
                    {subjectStats.completed} of {subjectStats.total} plans complete
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                  <div 
                    className="bg-blue-600 h-2.5 rounded-full" 
                    style={{ width: `${subjectStats.percentage}%` }}
                  ></div>
                </div>
                <div className="text-sm text-gray-500">
                  {subjectStats.percentage}% complete
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Plans Message */}
      {stats.total === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">You haven't created any learning plans yet.</p>
          <p className="mt-2">
            <a href="/dashboard" className="text-blue-600 hover:underline">
              Go to dashboard to create your first plan →
            </a>
          </p>
        </div>
      )}
    </div>
  );
};

export default ProgressTracker;