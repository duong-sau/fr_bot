import axios from 'axios';
import config from '../config';
import {
  getActiveBaseUrl,
  getServers as getStoredServers,
  setActiveServer as setStoredActive,
  setServerUrl as setStoredServerUrl
} from './apiConfig';

// Create axios instance with dynamic baseURL
const api = axios.create({
  baseURL: getActiveBaseUrl(config.API_BASE_URL),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Helper to refresh axios baseURL after settings change
export function refreshApiBaseUrl() {
  api.defaults.baseURL = getActiveBaseUrl(config.API_BASE_URL);
  return api.defaults.baseURL;
}

// Expose settings helpers to UI
export function getServers() {
  return getStoredServers(config.API_BASE_URL);
}

export function setActiveServer(key) {
  setStoredActive(key);
  return refreshApiBaseUrl();
}

export function setServerUrl(key, url) {
  const normalized = setStoredServerUrl(key, url);
  // If updating currently active server, refresh baseURL
  const { active } = getStoredServers(config.API_BASE_URL);
  if (active === key) {
    refreshApiBaseUrl();
  }
  return normalized;
}

// API service functions
export const apiService = {
  // Microservices management
  getMicroservices: async () => {
    const response = await api.get(config.endpoints.microservices);
    return response.data;
  },

  startMicroservice: async (id) => {
    const response = await api.put(`${config.endpoints.microservices}/${id}/start`);
    return response.data;
  },

  stopMicroservice: async (id) => {
    const response = await api.put(`${config.endpoints.microservices}/${id}/stop`);
    return response.data;
  },

  // Positions management
  getPositions: async () => {
    const response = await api.get(config.endpoints.positions);
    return response.data;
  },

  openPosition: async (symbol, size) => {
    const response = await api.post(config.endpoints.positionsOpen, {
      symbol,
      size
    });
    return response.data;
  },

  estimatePosition: async (symbol, size) => {
    const response = await api.post(config.endpoints.positionsEstimate, {
      symbol,
      size
    });
    return response.data;
  }
};

export default apiService;
