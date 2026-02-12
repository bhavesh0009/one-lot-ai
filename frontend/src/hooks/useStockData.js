import { useState, useCallback } from 'react';
import { fetchStockInfo, fetchStockHistory, fetchStockTechnicals, fetchStockOptionChain } from '../libs/api';

export const useStockData = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState([]);

  const addLog = (msg) => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), msg }]);
  };

  const loadStockData = useCallback(async (ticker) => {
    setLoading(true);
    setError(null);
    setLogs([]);
    setData(null);

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

      setData({
        basic: info.basic,
        banStatus: info.ban_status,
        latest_ohlcv: info.latest_ohlcv,
        history,
        technicals,
        chain: chainData,
        // Mocking trade recommendation for now as per plan
        recommendation: {
          ticker: ticker,
          strike: Math.round(info.latest_ohlcv.close), // Mock strike ATM
          type: "CE", // Mock
          entry: (info.latest_ohlcv.close * 0.01).toFixed(2), // Mock
          sl: (info.latest_ohlcv.close * 0.005).toFixed(2), // Mock
          target: (info.latest_ohlcv.close * 0.02).toFixed(2), // Mock
          lotSize: info.basic.lot_size,
          confidence: 'Mocked 85%'
        }
      });
      addLog("Analysis Complete.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to fetch data");
      addLog(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, logs, loadStockData };
};
