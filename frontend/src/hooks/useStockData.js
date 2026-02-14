import { useState, useCallback } from 'react';
import { fetchStockInfo, fetchStockHistory, fetchStockTechnicals, fetchStockOptionChain, fetchStockNews, fetchRecommendation } from '../libs/api';

export const useStockData = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState([]);
  const [recommendationLoading, setRecommendationLoading] = useState(false);

  const addLog = (msg) => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), msg }]);
  };

  const loadStockData = useCallback(async (ticker) => {
    setLoading(true);
    setError(null);
    setLogs([]);
    setData(null);
    setRecommendationLoading(false);

    try {
      addLog(`Fetching Info for ${ticker}...`);
      const info = await fetchStockInfo(ticker);
      addLog("Basic Info & Ban Status Loaded.");

      addLog("Fetching Historical Data...");
      const history = await fetchStockHistory(ticker);
      addLog(`Loaded ${history.length} days of history.`);

      addLog("Calculating Technicals...");
      const technicals = await fetchStockTechnicals(ticker);
      addLog("Technicals Calculated.");

      addLog("Fetching Option Chain...");
      let chainData = null;
      try {
        chainData = await fetchStockOptionChain(ticker);
        addLog("Option Chain Loaded.");
      } catch (e) {
        console.warn("Option chain fetch failed", e);
        addLog("Option Chain fetch failed (Angel One unavailable?).");
      }

      addLog("Fetching Stock News...");
      let newsData = null;
      try {
        newsData = await fetchStockNews(ticker);
        addLog("Stock News Loaded.");
      } catch (e) {
        console.warn("Stock news fetch failed", e);
        addLog("Stock news fetch failed.");
      }

      // Set data first so dashboard renders while recommendation loads
      setData({
        basic: info.basic,
        banStatus: info.ban_status,
        latest_ohlcv: info.latest_ohlcv,
        change: info.change,
        change_pct: info.change_pct,
        history,
        technicals,
        chain: chainData,
        news: newsData,
        recommendation: null,
      });
      setLoading(false);

      // Fetch recommendation in background (takes 10-30s)
      addLog("Generating AI Trade Recommendation...");
      setRecommendationLoading(true);
      try {
        const rec = await fetchRecommendation(ticker);
        setData(prev => prev ? { ...prev, recommendation: rec } : prev);
        addLog("AI Recommendation Ready.");
      } catch (e) {
        console.warn("Recommendation fetch failed", e);
        addLog("AI Recommendation failed.");
        setData(prev => prev ? { ...prev, recommendation: { error: e.message } } : prev);
      } finally {
        setRecommendationLoading(false);
      }

    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to fetch data");
      addLog(`Error: ${err.message}`);
      setLoading(false);
    }
  }, []);

  return { data, loading, error, logs, loadStockData, recommendationLoading };
};
