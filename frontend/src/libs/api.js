import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000,
});

export const fetchStockInfo = async (ticker) => {
  const response = await api.get(`/stock/${ticker}`);
  return response.data;
};

export const fetchStockHistory = async (ticker, days = 365) => {
  const response = await api.get(`/stock/${ticker}/history?days=${days}`);
  return response.data;
};

export const fetchStockTechnicals = async (ticker) => {
  const response = await api.get(`/stock/${ticker}/technicals`);
  return response.data;
};

export const fetchStockOptionChain = async (ticker) => {
  const response = await api.get(`/stock/${ticker}/chain`);
  return response.data;
};

export default api;
