import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { chatApi } from '../api/chatApi';
import { addMessage, setTyping } from '../store/slices/chatSlice';
import { populateFromAI, updateFromAI, setAISuggestions, setInteractionId } from '../store/slices/interactionSlice';
import './AIAssistant.css';

const AIAssistant = () => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);
  
  const dispatch = useDispatch();
  const { messages, isTyping } = useSelector((state) => state.chat);
  const { currentInteractionId } = useSelector((state) => state.interaction);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (e) => {
    e.preventDefault();
    const text = inputValue.trim();
    if (!text) return;

    // 1. Add user message
    dispatch(addMessage({ text, sender: 'user' }));
    setInputValue('');

    // 2. Set typing
    dispatch(setTyping(true));

    // 3. API Call
    try {
      const response = await chatApi.sendMessage(text, currentInteractionId);
      const { tool_used, result, message } = response;
      
      // Determine if success message (e.g. from logging or editing)
      const isSuccess = tool_used === 'log_interaction_tool' || tool_used === 'edit_interaction_tool';
      const displayText = isSuccess && !message.startsWith('❌') && !message.startsWith('⚠️') ? message : message;

      // 4a. Add AI Response message
      dispatch(addMessage({ 
        text: displayText, 
        sender: 'ai',
        success: isSuccess && !message.startsWith('❌') && !message.startsWith('⚠️') 
      }));

      // 4b. Dispatch to Interaction form based on tool
      if (tool_used === 'log_interaction_tool' && result?.status === 'created') {
        dispatch(populateFromAI(result));
        if (result.interaction_id) {
          dispatch(setInteractionId(result.interaction_id));
        }
      } else if (tool_used === 'edit_interaction_tool' && result?.status === 'updated') {
        if (result.changed_fields) {
           dispatch(updateFromAI(result.changed_fields));
        }
      } else if (tool_used === 'suggest_followup_tool' && result?.status === 'ok') {
        if (result.suggestions) {
           dispatch(setAISuggestions(result.suggestions));
        }
      }
      
    } catch (error) {
      console.error("Chat API Error:", error);
      dispatch(addMessage({ 
        text: "❌ Error connecting to AI Agent. Make sure the backend server is running.", 
        sender: 'ai' 
      }));
    } finally {
      // 5. Stop typing
      dispatch(setTyping(false));
    }
  };

  return (
    <div className="ai-panel-container">
      <div className="ai-header">
        <h2>🤖 AI Assistant</h2>
        <p>Log Interaction details here via chat</p>
      </div>

      <div className="chat-area">
        {/* Placeholder / Hint Bubble */}
        {messages.length === 0 && (
          <div className="message-wrapper ai">
            <div className="message-bubble ai">
              Log interaction details here (e.g., 'Met Dr. Smith, discussed Prodo-X efficacy, positive sentiment, shared brochure') or ask for help.
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg, index) => (
          <div key={index} className={`message-wrapper ${msg.sender}`}>
            <div className={`message-bubble ${msg.sender} ${msg.success ? 'success' : ''}`}>
              {msg.text}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="message-wrapper ai">
            <div className="message-bubble ai">
              <div className="typing-indicator">
                <div className="dot"></div>
                <div className="dot"></div>
                <div className="dot"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <form onSubmit={handleSend} className="input-form">
          <input
            type="text"
            placeholder="Describe Interaction..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isTyping}
          />
          <button type="submit" className="send-button" disabled={isTyping || !inputValue.trim()}>
            A Log
          </button>
        </form>
      </div>
    </div>
  );
};

export default AIAssistant;
