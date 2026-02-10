import React from 'react';

interface GameStatsProps {
  attempts: number;
  accuracy: number;
  timeTaken: number; // in seconds
}

const GameStats: React.FC<GameStatsProps> = ({ attempts, accuracy, timeTaken }) => {
  return (
    <div className="game-stats">
      <h2>Statistics</h2>
      <p>Attempts: {attempts}</p>
      <p>Accuracy: {accuracy}%</p>
      <p>Time: {timeTaken.toFixed(1)}s</p>
    </div>
  );
};

export default GameStats;