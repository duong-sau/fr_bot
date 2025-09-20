import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

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
