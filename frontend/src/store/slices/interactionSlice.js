import { createSlice } from '@reduxjs/toolkit';

const getTodayDate = () => {
  const today = new Date();
  return today.toISOString().split('T')[0];
};

const getCurrentTime = () => {
  const now = new Date();
  return now.toTimeString().split(' ')[0].substring(0, 5);
};

const initialState = {
  hcpName: "",
  interactionType: "Meeting",
  date: getTodayDate(),
  time: getCurrentTime(),
  attendees: "",
  topicsDiscussed: "",
  materialsShared: [],
  samplesDistributed: [],
  sentiment: "Neutral",
  outcomes: "",
  followUpActions: "",
  aiSuggestions: [],
  currentInteractionId: null,
  isLoading: false,
  error: null
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    updateField: (state, action) => {
      const { field, value } = action.payload;
      if (field in state) {
        state[field] = value;
      }
    },
    populateFromAI: (state, action) => {
      // action.payload should be the extractedData object from AI
      const data = action.payload;
      if (data.hcp_name) state.hcpName = data.hcp_name;
      if (data.interaction_type) state.interactionType = data.interaction_type;
      if (data.date) state.date = data.date;
      if (data.time) state.time = data.time;
      if (data.attendees) state.attendees = Array.isArray(data.attendees) ? data.attendees.join(", ") : data.attendees;
      if (data.topics_discussed) state.topicsDiscussed = data.topics_discussed;
      if (data.materials_shared) state.materialsShared = data.materials_shared;
      if (data.samples_distributed) state.samplesDistributed = data.samples_distributed;
      if (data.sentiment) state.sentiment = data.sentiment;
      if (data.outcomes) state.outcomes = data.outcomes;
      if (data.follow_up_actions) state.followUpActions = Array.isArray(data.follow_up_actions) ? data.follow_up_actions.join("\n") : data.follow_up_actions;
      if (data.interaction_id) state.currentInteractionId = data.interaction_id;
    },
    updateFromAI: (state, action) => {
      // action.payload should be the changedFields object from AI edit tool
      const data = action.payload;
      Object.keys(data).forEach(key => {
        // Map backend keys to frontend state keys
        const stateKey = key.replace(/_([a-z])/g, (g) => g[1].toUpperCase());
        if (stateKey in state) {
           if (Array.isArray(data[key]) && typeof state[stateKey] === 'string') {
               state[stateKey] = data[key].join(', ');
           } else {
               state[stateKey] = data[key];
           }
        }
      });
    },
    setAISuggestions: (state, action) => {
      state.aiSuggestions = action.payload;
    },
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
    resetForm: (state) => {
      return { ...initialState, date: getTodayDate(), time: getCurrentTime() };
    },
    setInteractionId: (state, action) => {
      state.currentInteractionId = action.payload;
    }
  }
});

export const {
  updateField,
  populateFromAI,
  updateFromAI,
  setAISuggestions,
  setLoading,
  setError,
  resetForm,
  setInteractionId
} = interactionSlice.actions;

export default interactionSlice.reducer;
