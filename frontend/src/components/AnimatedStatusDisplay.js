import React, { useEffect, useMemo } from 'react';
import { FiCheckCircle, FiAlertTriangle, FiLoader, FiRefreshCw, FiClock, FiFileText, FiType, FiDownload } from 'react-icons/fi';

const AnimatedStatusDisplay = ({ status, error, onReset, jobId, originalFile }) => {
  // Smart API URL configuration (same logic as upload form)
  const API_BASE_URL = useMemo(() => {
    const isDevelopment = process.env.NODE_ENV === 'development';
    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname === '0.0.0.0';
    
    if (process.env.REACT_APP_API_BASE_URL) {
      return process.env.REACT_APP_API_BASE_URL;
    } else if (isDevelopment || isLocalhost) {
      return 'http://localhost:5001';
    } else {
      return 'https://api.capvid.app';
    }
  }, []);
  
  useEffect(() => {
    // Cleanup on page unload/refresh - but only after sufficient time
    const handleBeforeUnload = () => {
      // Only cleanup if job has been completed for more than 5 minutes
      if (jobId && (status?.status === 'completed' || status?.status === 'failed')) {
        // Don't immediately cleanup - let server handle it with its retention policy
        console.log(`Job ${jobId} marked for server-side cleanup`);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [jobId, status, API_BASE_URL]);

  const handleDownload = async (downloadUrl) => {
    try {
      const link = document.createElement('a');
      link.href = `${API_BASE_URL}${downloadUrl}`;
      link.target = '_blank';
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      console.log(`Download initiated for job ${jobId}. File will be available for 1 hour.`);
      
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download failed. Please try again.');
    }
  };

  if (error) {
    const isJobExpired = typeof error === 'string' && error.includes('expired');
    
    return (
      <div className="w-full max-w-md mx-auto p-2">
        <div className="bg-white bg-opacity-10 backdrop-blur-md rounded-xl p-4 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-red-900 bg-opacity-30 mb-3">
            <FiAlertTriangle className="h-6 w-6 text-red-400" />
          </div>
          <h3 
            className="text-lg font-semibold text-white mb-2"
            style={{ fontFamily: 'Urbanist, sans-serif' }}
          >
            {isJobExpired ? 'Session Expired' : 'Processing Failed'}
          </h3>
          <p 
            className="text-gray-300 text-xs mb-3"
            style={{ fontFamily: 'Urbanist, sans-serif' }}
          >
            {typeof error === 'string' ? error : 'An error occurred during processing.'}
          </p>
          <button
            onClick={onReset}
            className="bg-cyan-600 hover:bg-cyan-700 text-white font-semibold py-2 px-4 rounded-lg transition-all duration-300 hover:scale-105 text-sm"
            style={{ fontFamily: 'Urbanist, sans-serif' }}
          >
            <FiRefreshCw className="mr-2 inline" /> {isJobExpired ? 'Start Over' : 'Try Again'}
          </button>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="w-full max-w-md mx-auto p-2">
        <div className="bg-white bg-opacity-10 backdrop-blur-md rounded-xl p-4 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-purple-900 bg-opacity-30 mb-3">
            <FiLoader className="h-6 w-6 text-purple-400 animate-spin" />
          </div>
          <h3 
            className="text-lg font-semibold text-white mb-2"
            style={{ fontFamily: 'Urbanist, sans-serif' }}
          >
            Initializing...
          </h3>
          <p 
            className="text-gray-300 text-xs"
            style={{ fontFamily: 'Urbanist, sans-serif' }}
          >
            Getting things ready for your video processing
          </p>
        </div>
      </div>
    );
  }

  const getStatusInfo = () => {
    switch (status.status) {
      case 'uploaded':
        return {
          icon: <FiClock className="h-6 w-6 text-purple-400" />,
          title: 'Video Uploaded',
          message: 'Preparing to process your video...',
          progress: 10,
          color: 'purple'
        };
      case 'transcribing':
        return {
          icon: <FiLoader className="h-6 w-6 text-blue-400 animate-spin" />,
          title: 'Transcribing Audio',
          message: 'Converting speech to text using AI...',
          progress: 30,
          color: 'blue'
        };
      case 'generating_captions':
        return {
          icon: <FiFileText className="h-6 w-6 text-purple-400" />,
          title: 'Generate Subtitles',
          message: 'Creating subtitle file from transcription...',
          progress: 60,
          color: 'purple'
        };
      case 'embedding_subtitles':
        return {
          icon: <FiType className="h-6 w-6 text-pink-400" />,
          title: 'Overlay Captions',
          message: 'Embedding subtitles into your video...',
          progress: 80,
          color: 'pink'
        };
      case 'completed':
        return {
          icon: <FiCheckCircle className="h-6 w-6 text-green-400" />,
          title: 'Complete Processing',
          message: 'Your video with subtitles is ready to download!',
          progress: 100,
          color: 'green'
        };
      case 'completed_srt_only':
        return {
          icon: <FiAlertTriangle className="h-6 w-6 text-yellow-400" />,
          title: 'Video Processing Failed',
          message: 'Unable to embed subtitles into video. Please try again with a different video format.',
          progress: 100,
          color: 'yellow'
        };
      case 'failed':
        return {
          icon: <FiAlertTriangle className="h-6 w-6 text-red-400" />,
          title: 'Processing Failed',
          message: status.error || 'An error occurred during processing.',
          progress: 100,
          color: 'red'
        };
      default:
        return {
          icon: <FiLoader className="h-6 w-6 text-purple-400 animate-spin" />,
          title: 'Processing',
          message: 'Working on your video...',
          progress: 50,
          color: 'purple'
        };
    }
  };

  const { icon, title, message, progress, color } = getStatusInfo();

  return (
    <div className="w-full max-w-md mx-auto p-2">
      <div className="bg-white bg-opacity-10 backdrop-blur-md rounded-xl p-4 text-center">
        
        <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full bg-${color}-900 bg-opacity-30 mb-3`}>
          {React.cloneElement(icon, { className: "h-6 w-6 " + icon.props.className.split(' ').slice(2).join(' ') })}
        </div>
        
        <h3 
          className="text-lg font-semibold text-white mb-2"
          style={{ fontFamily: 'Urbanist, sans-serif' }}
        >
          {title}
        </h3>
        
        <p 
          className="text-gray-300 text-xs mb-3"
          style={{ fontFamily: 'Urbanist, sans-serif' }}
        >
          {message}
        </p>
        
        {status.filename && (
          <div className="mb-3">
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-black bg-opacity-30 text-xs text-gray-300">
              <FiFileText className="mr-2 h-3 w-3" />
              <span style={{ fontFamily: 'Urbanist, sans-serif' }}>
                {status.filename}
              </span>
            </div>
          </div>
        )}

        {/* Enhanced Progress Bar */}
        <div className="w-full mx-auto bg-white bg-opacity-20 rounded-full h-3 mb-4 relative overflow-hidden">
          <div 
            className={`bg-gradient-to-r from-gray-800 to-black h-3 rounded-full transition-all duration-700 ease-out relative`}
            style={{width: `${progress}%`}}
          >
            <div className="absolute inset-0 bg-white bg-opacity-20 animate-pulse"></div>
          </div>
          <div className="absolute right-2 top-0 bottom-0 flex items-center">
            <span className="text-xs font-medium text-white opacity-80" style={{ fontFamily: 'Urbanist, sans-serif' }}>
              {progress}%
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-2 justify-center items-center">
          {status.status === 'completed' && status.download_url && (
            <button
              onClick={() => handleDownload(status.download_url)}
              className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg transition-all duration-300 hover:scale-105 flex items-center justify-center text-sm"
              style={{ fontFamily: 'Urbanist, sans-serif' }}
            >
              <FiDownload className="mr-2 h-4 w-4" />
              Download Video with Subtitles
            </button>
          )}
          
          <button
            onClick={onReset}
            className={`font-semibold py-2 px-4 rounded-lg transition-all duration-300 text-sm ${
              status.status === 'completed' || status.status === 'completed_srt_only' || status.status === 'failed' 
                ? 'bg-cyan-600 hover:bg-cyan-700 text-white hover:scale-105' 
                : 'bg-gray-600 bg-opacity-50 cursor-not-allowed text-gray-400'
            }`}
            style={{ fontFamily: 'Urbanist, sans-serif' }}
            disabled={!(status.status === 'completed' || status.status === 'completed_srt_only' || status.status === 'failed')}
          >
            <FiRefreshCw className="mr-2 inline" /> Process Another Video
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnimatedStatusDisplay;
