import React, { useState, useEffect, useRef } from 'react';
import { Search } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

const TickerSearch = ({ onSelect, loading }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const inputRef = useRef(null);
    const dropdownRef = useRef(null);
    const debounceRef = useRef(null);

    // Debounced search
    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);

        if (query.length < 1) {
            setResults([]);
            setShowDropdown(false);
            return;
        }

        debounceRef.current = setTimeout(async () => {
            try {
                const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
                const data = await res.json();
                if (data.results && data.results.length > 0) {
                    setResults(data.results);
                    setShowDropdown(true);
                    setSelectedIndex(-1);
                } else {
                    setResults([]);
                    setShowDropdown(false);
                }
            } catch (err) {
                console.error('Search failed:', err);
                setResults([]);
            }
        }, 300);

        return () => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
        };
    }, [query]);

    // Close dropdown on outside click
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (
                dropdownRef.current && !dropdownRef.current.contains(e.target) &&
                inputRef.current && !inputRef.current.contains(e.target)
            ) {
                setShowDropdown(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelect = (item) => {
        setQuery(item.symbol);
        setShowDropdown(false);
        onSelect(item.symbol);
    };

    const handleKeyDown = (e) => {
        if (!showDropdown || results.length === 0) {
            if (e.key === 'Enter' && query.length > 0) {
                e.preventDefault();
                setShowDropdown(false);
                onSelect(query.toUpperCase());
            }
            return;
        }

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setSelectedIndex(prev => Math.min(prev + 1, results.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setSelectedIndex(prev => Math.max(prev - 1, -1));
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (selectedIndex >= 0 && selectedIndex < results.length) {
                handleSelect(results[selectedIndex]);
            } else if (query.length > 0) {
                setShowDropdown(false);
                onSelect(query.toUpperCase());
            }
        } else if (e.key === 'Escape') {
            setShowDropdown(false);
        }
    };

    // Highlight matching text
    const highlightMatch = (text, query) => {
        if (!query) return text;
        const idx = text.toUpperCase().indexOf(query.toUpperCase());
        if (idx === -1) return text;
        return (
            <>
                {text.slice(0, idx)}
                <span style={{ color: '#34d399', fontWeight: 700 }}>{text.slice(idx, idx + query.length)}</span>
                {text.slice(idx + query.length)}
            </>
        );
    };

    return (
        <div style={{ position: 'relative', width: '100%', maxWidth: '36rem', margin: '0 auto' }}>
            {/* Input */}
            <div style={{ position: 'relative' }}>
                <div style={{
                    position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)',
                    pointerEvents: 'none', color: '#64748b'
                }}>
                    <Search size={20} />
                </div>
                <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value.toUpperCase())}
                    onKeyDown={handleKeyDown}
                    onFocus={() => { if (results.length > 0) setShowDropdown(true); }}
                    placeholder="Search by ticker or company name..."
                    style={{
                        width: '100%',
                        paddingLeft: '44px',
                        paddingRight: '110px',
                        paddingTop: '16px',
                        paddingBottom: '16px',
                        background: '#0f172a',
                        border: '1px solid #1e293b',
                        borderRadius: '16px',
                        fontSize: '1.05rem',
                        color: '#fff',
                        outline: 'none',
                        transition: 'border-color 0.2s, box-shadow 0.2s',
                        boxShadow: '0 10px 25px -5px rgba(0,0,0,0.3)',
                        boxSizing: 'border-box',
                    }}
                    onFocusCapture={(e) => {
                        e.target.style.borderColor = '#10b981';
                        e.target.style.boxShadow = '0 0 0 3px rgba(16,185,129,0.15), 0 10px 25px -5px rgba(0,0,0,0.3)';
                    }}
                    onBlurCapture={(e) => {
                        e.target.style.borderColor = '#1e293b';
                        e.target.style.boxShadow = '0 10px 25px -5px rgba(0,0,0,0.3)';
                    }}
                />
                <button
                    onClick={() => { if (query) { setShowDropdown(false); onSelect(query.toUpperCase()); } }}
                    disabled={loading || !query}
                    style={{
                        position: 'absolute',
                        right: '8px',
                        top: '8px',
                        bottom: '8px',
                        background: loading ? '#374151' : '#059669',
                        color: '#fff',
                        border: 'none',
                        padding: '0 20px',
                        borderRadius: '12px',
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        opacity: (!query || loading) ? 0.5 : 1,
                        transition: 'background 0.2s, opacity 0.2s',
                    }}
                    onMouseEnter={(e) => { if (!loading) e.target.style.background = '#10b981'; }}
                    onMouseLeave={(e) => { if (!loading) e.target.style.background = '#059669'; }}
                >
                    {loading ? 'Analyzing...' : 'Analyze'}
                </button>
            </div>

            {/* Dropdown */}
            {showDropdown && results.length > 0 && (
                <div
                    ref={dropdownRef}
                    style={{
                        position: 'absolute',
                        top: 'calc(100% + 4px)',
                        left: 0,
                        right: 0,
                        background: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '12px',
                        overflow: 'hidden',
                        zIndex: 100,
                        boxShadow: '0 20px 50px -10px rgba(0,0,0,0.5)',
                        maxHeight: '320px',
                        overflowY: 'auto',
                    }}
                >
                    {results.map((item, idx) => (
                        <div
                            key={`${item.symbol}-${idx}`}
                            onClick={() => handleSelect(item)}
                            onMouseEnter={() => setSelectedIndex(idx)}
                            style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '10px 16px',
                                cursor: 'pointer',
                                background: idx === selectedIndex ? '#334155' : 'transparent',
                                borderBottom: idx < results.length - 1 ? '1px solid #293548' : 'none',
                                transition: 'background 0.1s',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                <span style={{
                                    background: '#0f172a',
                                    padding: '3px 8px',
                                    borderRadius: '6px',
                                    fontFamily: 'monospace',
                                    fontWeight: 700,
                                    fontSize: '0.85rem',
                                    color: '#e2e8f0',
                                    minWidth: '80px',
                                    textAlign: 'center',
                                    border: '1px solid #334155',
                                }}>
                                    {highlightMatch(item.symbol, query)}
                                </span>
                                <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                                    {highlightMatch(item.name || '', query)}
                                </span>
                            </div>
                            <span style={{ color: '#475569', fontSize: '0.7rem' }}>NSE</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default TickerSearch;
