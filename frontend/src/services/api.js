import axios from 'axios';
import { API_BASE_URL } from '../config';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      const message = error.response.data?.detail || error.response.data || error.message;
      return Promise.reject(new Error(message));
    }

    if (error.request) {
      return Promise.reject(new Error('Network error: no response from API')); 
    }

    return Promise.reject(error);
  }
);

export const fetchDisasters = async () => {
  return apiClient.get('/api/disasters');
};

export const fetchDamageZones = async (eventId) => {
  return apiClient.get(`/api/disasters/${eventId}/damage_zones`);
};

export const fetchDisasterSummary = async (eventId) => {
  return apiClient.get(`/api/disasters/${eventId}/summary`);
};

export const fetchAlerts = async (eventId) => {
  return apiClient.get(`/api/disasters/${eventId}/alerts`);
};

export const fetchAllocationRecommendations = async (eventId) => {
  return apiClient.get(`/api/resources/allocate/${eventId}`);
};

export const deployResources = async (deployment) => {
  return apiClient.post('/api/resources/deploy', deployment);
};
