import React from 'react';
import InteractionForm from './components/InteractionForm';
import AIAssistant from './components/AIAssistant';
import './App.css';

function App() {
  return (
    <div className="app-container">
      <div className="left-panel">
        <InteractionForm />
      </div>
      <div className="right-panel">
        <AIAssistant />
      </div>
    </div>
  );
}

export default App;
