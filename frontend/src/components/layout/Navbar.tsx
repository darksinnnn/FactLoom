import React, { useState, useEffect } from 'react';
import { LoomMark } from '../identity/LoomMark';
import { Wordmark } from '../identity/Wordmark';
import { useFactLoomStore, type NavTab } from '../../store/factsStore';
import { 
  GitMerge, 
  MagnifyingGlass, 
  FileText, 
  Question, 
  ShieldCheck, 
  UploadSimple,
  SquaresFour,
  Sun,
  Moon
} from '@phosphor-icons/react';

export const Navbar: React.FC = () => {
  const { activeTab, setActiveTab } = useFactLoomStore();

  const [theme, setTheme] = useState<'dark' | 'paper'>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('factloom-theme') as 'dark' | 'paper') || 'dark';
    }
    return 'dark';
  });

  useEffect(() => {
    if (theme === 'paper') {
      document.documentElement.setAttribute('data-theme', 'paper');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem('factloom-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'paper' : 'dark'));
  };

  const navItems: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: 'command', label: 'Command', icon: <SquaresFour size={16} /> },
    { id: 'reconciliation', label: 'Reconciliation', icon: <GitMerge size={16} /> },
    { id: 'explorer', label: 'Fact Explorer', icon: <MagnifyingGlass size={16} /> },
    { id: 'evidence', label: 'Evidence', icon: <FileText size={16} /> },
    { id: 'ask', label: 'Ask', icon: <Question size={16} /> },
    { id: 'limitations', label: 'Limitations', icon: <ShieldCheck size={16} /> },
    { id: 'upload', label: 'Upload', icon: <UploadSimple size={16} /> },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[var(--loom-ink)]/90 backdrop-blur-md border-b border-[var(--loom-card-border)] px-6 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand identity */}
        <div 
          onClick={() => setActiveTab('command')}
          className="flex items-center gap-3.5 cursor-pointer group select-none"
        >
          <LoomMark size={32} className="transition-transform group-hover:scale-105" />
          <Wordmark showTagline={false} />
          <span className="hidden sm:inline-block px-1.5 py-0.5 text-[9px] font-mono-tabular uppercase tracking-widest text-[var(--loom-verified)] bg-[var(--loom-verified)]/10 border border-[var(--loom-verified)]/20 rounded">
            v0.1.0
          </span>
        </div>

        {/* Navigation items + Theme Toggle */}
        <div className="flex items-center gap-2">
          <nav className="flex items-center gap-1 overflow-x-auto py-1">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveTab(item.id);
                    window.location.hash = item.id;
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-body tracking-wide transition-all rounded ${
                    isActive
                      ? 'text-[var(--loom-paper)] bg-[var(--loom-surface)] border border-[var(--loom-hairline)] font-medium shadow-sm'
                      : 'text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:bg-[var(--loom-surface)]/50'
                  }`}
                >
                  <span className={isActive ? 'text-[var(--loom-verified)]' : 'text-[var(--loom-thread)]'}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Warm Paper / Velvet Dark Theme Toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle visual theme"
            title={theme === 'dark' ? "Switch to Warm Ledger Paper theme" : "Switch to Velvet Slate Dark theme"}
            className="flex items-center gap-1.5 px-2.5 py-1.5 ml-1 text-xs font-mono-tabular tracking-wide transition-all rounded border border-[var(--loom-card-border)] bg-[var(--loom-surface)] text-[var(--loom-thread)] hover:text-[var(--loom-paper)] hover:border-[var(--loom-verified)]/40 cursor-pointer shadow-sm select-none"
          >
            {theme === 'dark' ? (
              <>
                <Moon size={14} className="text-[var(--loom-thread)]" />
                <span className="text-[10px] uppercase font-bold tracking-wider">Dark</span>
              </>
            ) : (
              <>
                <Sun size={14} className="text-[#B45309]" />
                <span className="text-[10px] uppercase font-bold tracking-wider text-[#1B1B18]">Paper</span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
};

