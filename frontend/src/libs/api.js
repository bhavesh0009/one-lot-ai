import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
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

export const fetchMarketNews = async () => {
  const response = await api.get('/news/market');
  return response.data;
};

export const fetchStockNews = async (ticker) => {
  const response = await api.get(`/stock/${ticker}/news`);
  return response.data;
};

export const fetchRecommendation = async (ticker) => {
  const response = await api.get(`/stock/${ticker}/recommendation`, { timeout: 120000 });
  return response.data;
};

export const fetchRecommendations = async (limit = 100) => {
  const response = await api.get(`/recommendations?limit=${limit}`);
  return response.data;
};

export default api;
