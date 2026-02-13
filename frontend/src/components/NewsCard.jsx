
import React from 'react';
import { ExternalLink, RefreshCw, Newspaper } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const NewsCard = ({ news, loading, title = "News", onRefresh }) => {
    return (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 h-full flex flex-col">
            <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-2">
                    <Newspaper className="w-5 h-5 text-indigo-400" />
                    <h2 className="font-semibold text-slate-100">{title}</h2>
                </div>
                {onRefresh && (
                    <button
                        onClick={onRefresh}
                        disabled={loading}
                        className="p-1 hover:bg-slate-800 rounded-full transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                )}
            </div>

            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {loading && !news ? (
                    <div className="animate-pulse space-y-3">
                        <div className="h-4 bg-slate-800 rounded w-3/4"></div>
                        <div className="h-4 bg-slate-800 rounded w-full"></div>
                        <div className="h-4 bg-slate-800 rounded w-5/6"></div>
                    </div>
                ) : news?.error ? (
                    <div className="text-red-400 text-sm p-3 bg-red-900/20 rounded border border-red-900/50">
                        {news.error}
                    </div>
                ) : news?.text ? (
                    <div className="space-y-4">
                        <div className="text-slate-300 text-sm leading-relaxed">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    ul: ({ node, ...props }) => <ul className="list-disc pl-5 space-y-2 mb-4" {...props} />,
                                    ol: ({ node, ...props }) => <ol className="list-decimal pl-5 space-y-2 mb-4" {...props} />,
                                    li: ({ node, ...props }) => <li className="text-slate-300 text-sm pl-1" {...props} />,
                                    strong: ({ node, ...props }) => <strong className="font-semibold text-indigo-300" {...props} />,
                                    p: ({ node, ...props }) => <p className="mb-3 last:mb-0" {...props} />,
                                    h1: ({ node, ...props }) => <h1 className="text-lg font-bold text-slate-100 mt-4 mb-2" {...props} />,
                                    h2: ({ node, ...props }) => <h2 className="text-base font-bold text-slate-100 mt-3 mb-2" {...props} />,
                                    h3: ({ node, ...props }) => <h3 className="text-sm font-bold text-slate-100 mt-2 mb-1" {...props} />,
                                    blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-indigo-500 pl-4 italic text-slate-400 my-4" {...props} />,
                                }}
                            >
                                {news.text}
                            </ReactMarkdown>
                        </div>

                        {news.sources && news.sources.length > 0 && (
                            <div className="mt-4 pt-4 border-t border-slate-800">
                                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Sources</h4>
                                <div className="flex flex-wrap gap-2">
                                    {news.sources.map((source, index) => (
                                        <a
                                            key={index}
                                            href={source.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-900/20 px-2 py-1 rounded border border-indigo-900/50 transition-colors"
                                        >
                                            <span>{source.title || 'Source'}</span>
                                            <ExternalLink className="w-3 h-3" />
                                        </a>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="text-slate-500 text-sm text-center py-8">
                        No news available at the moment.
                    </div>
                )}
            </div>
        </div>
    );
};

export default NewsCard;
