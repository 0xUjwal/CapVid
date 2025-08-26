import React from 'react';
import { FiGithub } from 'react-icons/fi';

const GitHubFooter = () => {
  return (
    <div className="fixed bottom-4 right-4 lg:bottom-6 lg:right-6 z-50">
      <a
        href="https://github.com/0xUjwal/CapVid"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center space-x-2 bg-black bg-opacity-50 backdrop-blur-sm text-white px-3 py-2 lg:px-4 rounded-full hover:bg-opacity-70 transition-all duration-300 hover:scale-105 shadow-lg"
        style={{ fontFamily: 'Urbanist, sans-serif' }}
      >
        <FiGithub className="h-4 w-4 lg:h-5 lg:w-5" />
        <span className="text-xs lg:text-sm font-medium hidden sm:inline">Star this repository</span>
        <span className="text-xs font-medium sm:hidden">Star</span>
      </a>
    </div>
  );
};

export default GitHubFooter;
