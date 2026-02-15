import { Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import DashboardPage from './pages/DashboardPage';
import RecommendationsPage from './pages/RecommendationsPage';

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-emerald-500/30">
      <Header />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
      </Routes>
    </div>
  );
}
