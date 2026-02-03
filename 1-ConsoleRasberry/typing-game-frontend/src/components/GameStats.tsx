import React from 'react';

interface GameStatsProps {
  attempts: number;
  accuracy: number;
  timeTaken: number; // in seconds
}

const GameStats: React.FC<GameStatsProps> = ({ attempts, accuracy, timeTaken }) => {
  return (
    <div className="game-stats">
      <div className="stat-item">
        <span className="stat-label">Attempts</span>
        <span className="stat-value">{attempts}</span>
      </div>
      <div className="stat-item">
        <span className="stat-label">Accuracy</span>
        <span className="stat-value">{accuracy}%</span>
      </div>
      <div className="stat-item">
        <span className="stat-label">Time</span>
        <span className="stat-value">{timeTaken.toFixed(1)}s</span>
      </div>
    </div>
  );
};

export default GameStats;