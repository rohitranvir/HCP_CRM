import React from 'react';
import { useSelector } from 'react-redux';
import SentimentSelector from './SentimentSelector';
import './InteractionForm.css';

const InteractionForm = () => {
  const {
    hcpName,
    interactionType,
    date,
    time,
    attendees,
    topicsDiscussed,
    materialsShared,
    samplesDistributed,
    sentiment,
    outcomes,
    followUpActions,
    aiSuggestions
  } = useSelector((state) => state.interaction);

  return (
    <div className="form-container">
      <div className="header">
        <h2>Log HCP Interaction</h2>
      </div>

      <div className="content">
        {/* Section: Interaction Details */}
        <div className="section">
          <h3 className="section-title">Interaction Details</h3>
          
          <div className="form-group">
            <label>HCP Name</label>
            <input type="text" value={hcpName} disabled placeholder="Search and select HCP..." />
          </div>

          <div className="form-group">
            <label>Interaction Type</label>
            <select value={interactionType} disabled>
              <option value="Meeting">Meeting</option>
              <option value="Call">Call</option>
              <option value="Email">Email</option>
              <option value="Conference">Conference</option>
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Date</label>
              <input type="date" value={date} disabled />
            </div>
            <div className="form-group">
              <label>Time</label>
              <input type="time" value={time} disabled />
            </div>
          </div>

          <div className="form-group">
            <label>Attendees</label>
            <input type="text" value={attendees} disabled placeholder="E.g., Rep, Medical Manager..." />
          </div>
        </div>

        {/* Section: Topics Discussed */}
        <div className="section">
          <h3 className="section-title">Topics Discussed</h3>
          <div className="form-group">
            <textarea 
              value={topicsDiscussed} 
              disabled 
              placeholder="What was discussed during the interaction?"
            />
          </div>
          <button className="link-button" disabled>
            🎤 Summarize from Voice Note (Requires Consent)
          </button>
        </div>

        {/* Section: Materials Shared / Samples Distributed */}
        <div className="section">
          <h3 className="section-title">Materials Shared / Samples Distributed</h3>
          
          <div className="form-group">
            <label>Materials Shared</label>
            <div className="list-display">
              {materialsShared && materialsShared.length > 0 ? (
                <ul>
                  {materialsShared.map((item, idx) => <li key={idx}>{item}</li>)}
                </ul>
              ) : (
                "No materials shared."
              )}
            </div>
            <button className="action-button" disabled>Search/Add</button>
          </div>

          <div className="form-group">
            <label>Samples Distributed</label>
            <div className="list-display">
              {samplesDistributed && samplesDistributed.length > 0 ? (
                <ul>
                  {samplesDistributed.map((item, idx) => <li key={idx}>{item}</li>)}
                </ul>
              ) : (
                "No samples distributed."
              )}
            </div>
            <button className="action-button" disabled>+ Add Sample</button>
          </div>
        </div>

        {/* Section: Observed/Inferred HCP Sentiment */}
        <div className="section">
          <h3 className="section-title">Observed/Inferred HCP Sentiment</h3>
          <SentimentSelector value={sentiment} />
        </div>

        {/* Section: Outcomes */}
        <div className="section">
          <h3 className="section-title">Outcomes</h3>
          <div className="form-group">
            <textarea 
              value={outcomes} 
              disabled 
              placeholder="What were the outcomes of this interaction?"
            />
          </div>
        </div>

        {/* Section: Follow-up Actions */}
        <div className="section">
          <h3 className="section-title">Follow-up Actions</h3>
          <div className="form-group">
            <textarea 
              value={followUpActions} 
              disabled 
              placeholder="Any planned follow-up actions?"
            />
          </div>

          {aiSuggestions && aiSuggestions.length > 0 && (
            <div className="ai-suggestions-box">
              <h4>✨ AI Suggested Follow-ups:</h4>
              <ul className="ai-suggestions-list">
                {aiSuggestions.map((suggestion, idx) => (
                  <li key={idx}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

export default InteractionForm;
