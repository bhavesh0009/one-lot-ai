import React from 'react';
import { Brain, Clock } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export default function Header() {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 hover:opacity-90 transition-opacity">
          <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-cyan-600 rounded-lg flex items-center justify-center">
            <Brain className="text-white w-5 h-5" />
          </div>
          <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
            One Lot AI
          </span>
        </Link>

        <nav className="flex items-center gap-6">
          <Link
            to="/"
            className={`text-sm font-medium transition-colors ${
              isActive('/') ? 'text-emerald-400' : 'text-slate-400 hover:text-emerald-300'
            }`}
          >
            Dashboard
          </Link>
          <Link
            to="/recommendations"
            className={`text-sm font-medium transition-colors ${
              isActive('/recommendations') ? 'text-emerald-400' : 'text-slate-400 hover:text-emerald-300'
            }`}
          >
            All Recommendations
          </Link>
        </nav>

        <div className="flex items-center gap-4 text-sm text-slate-400">
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" /> Market Open
          </span>
          <div className="w-px h-4 bg-slate-800"></div>
          <span className="text-emerald-500 font-medium">NIFTY (Live)</span>
        </div>
      </div>
    </header>
  );
}
