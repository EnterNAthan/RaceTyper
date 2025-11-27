import React from 'react';

interface ProgressBarProps {
    progress: number; // Progress should be a value between 0 and 100
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress }) => {
    return (
        <div className="progress-bar-container">
            <div className="progress-bar" style={{ width: `${progress}%` }} />
        </div>
    );
};

export default ProgressBar;