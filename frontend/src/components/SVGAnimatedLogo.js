import React, { useEffect, useRef } from 'react';
import anime from 'animejs/lib/anime.es.js';

const SVGAnimatedLogo = ({ className = '' }) => {
  const svgRef = useRef(null);

  useEffect(() => {
    if (svgRef.current) {
      const paths = svgRef.current.querySelectorAll('.line');
      
      // Set initial state for all paths
      anime.set(paths, {
        strokeDashoffset: anime.setDashoffset
      });

      // Animate the SVG path drawing using anime.js v3 syntax
      anime({
        targets: paths,
        strokeDashoffset: [anime.setDashoffset, 0],
        easing: 'easeInOutCubic',
        duration: 2000,
        delay: anime.stagger(300),
        direction: 'alternate',
        loop: true,
        autoplay: true
      });
    }
  }, []);

  return (
    <div className={`svg-logo-container ${className}`} style={{ 
      width: '100%', 
      maxWidth: '4800px',
      transformOrigin: 'center',
      overflow: 'visible',
      display: 'flex',
      justifyContent: 'center'
    }}>
      <svg 
        ref={svgRef}
        viewBox="0 0 1000 200" 
        className="w-full h-auto max-w-none"
        style={{
          stroke: '#FFFFFF',
          fill: 'none',
          strokeWidth: '8',
          strokeLinecap: 'square',
          strokeLinejoin: 'miter',
          width: '100%',
          maxWidth: '4800px',
          height: 'auto',
          transform: 'scale(1.1)'
        }}
      >
        {/* C - Futuristic, angular C with cut corners */}
        <path 
          className="line" 
          d="M140 70 L90 70 L70 80 L70 120 L90 130 L140 130"
        />
        
        {/* A - Wide, tech-inspired A with horizontal bar */}
        <path 
          className="line" 
          d="M180 130 L200 70 L220 130 M190 105 L210 105"
        />
        
        {/* P - Bold, geometric P with sharp angles */}
        <path 
          className="line" 
          d="M260 130 L260 70 L310 70 L330 80 L330 95 L310 105 L260 105"
        />
        
        {/* V - Dramatic, wide V shape */}
        <path 
          className="line" 
          d="M380 70 L420 130 L460 70"
        />
        
        {/* I - Extended, futuristic I with wide serifs */}
        <path 
          className="line" 
          d="M500 70 L580 70 M540 70 L540 130 M500 130 L580 130"
        />
        
        {/* D - Angular, tech-style D with beveled edges */}
        <path 
          className="line" 
          d="M620 130 L620 70 L670 70 L700 85 L710 100 L710 105 L700 115 L670 130 L620 130"
        />
      </svg>
    </div>
  );
};

export default SVGAnimatedLogo;
