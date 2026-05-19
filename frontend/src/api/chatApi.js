import axios from 'axios';

// Note: Vite uses VITE_ prefix for environment variables by default.
// If using REACT_APP_, it needs to be explicitly loaded via vite.config.js or we just fallback to the direct URL.
const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const chatApi = {
  sendMessage: async (message, interactionId = null) => {
    const payload = { message };
    if (interactionId) {
      payload.interaction_id = interactionId;
    }
    const response = await apiClient.post('/chat/', payload);
    return response.data;
  },

  getInteractions: async () => {
    const response = await apiClient.get('/interactions/');
    return response.data;
  },

  searchHCP: async (name) => {
    const response = await apiClient.get(`/hcp/search/?name=${encodeURIComponent(name)}`);
    return response.data;
  }
};
