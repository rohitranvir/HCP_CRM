import React from 'react';
import './SentimentSelector.css';

const SentimentSelector = ({ value }) => {
  return (
    <div className="sentiment-group">
      <label className={`radio-label ${value === 'Positive' ? 'selected' : ''}`}>
        <input type="radio" value="Positive" checked={value === 'Positive'} disabled />
        <span className="emoji">😊</span> Positive
      </label>
      
      <label className={`radio-label ${value === 'Neutral' ? 'selected' : ''}`}>
        <input type="radio" value="Neutral" checked={value === 'Neutral'} disabled />
        <span className="emoji">😐</span> Neutral
      </label>
      
      <label className={`radio-label ${value === 'Negative' ? 'selected' : ''}`}>
        <input type="radio" value="Negative" checked={value === 'Negative'} disabled />
        <span className="emoji">😟</span> Negative
      </label>
    </div>
  );
};

export default SentimentSelector;
