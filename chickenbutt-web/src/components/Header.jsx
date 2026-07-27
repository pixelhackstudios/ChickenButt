import { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';


export default function Header() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    // Initialize on mount
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  const handleNavClick = (e, targetId) => {
    closeMobileMenu();
    if (targetId === 'styleguide') {
      e.preventDefault();
      window.location.hash = '#styleguide';
      return;
    }
    e.preventDefault();
    if (window.lenis) {
      if (targetId === 'top') {
        window.lenis.scrollTo(0);
      } else {
        const element = document.getElementById(targetId);
        if (element) {
          window.lenis.scrollTo(element);
        }
      }
    } else {
      if (targetId === 'top') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        const element = document.getElementById(targetId);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' });
        }
      }
    }
  };

  return (
    <div className={`fixed left-0 right-0 z-50 flex flex-col items-center pointer-events-none transition-all duration-200 ${isScrolled ? 'top-0 px-0' : 'top-4 px-4'}`}>
      <header className={`pointer-events-auto flex items-center justify-between h-14 px-5 border-(--border-soft) bg-(--bg)/90 backdrop-blur-md shadow-sm w-full transition-all duration-300 ${isScrolled ? 'max-w-full rounded-none border-b' : 'max-w-6xl rounded-full border'}`}>
        <a href="#top" onClick={(e) => handleNavClick(e, 'top')} className="flex items-center gap-3 focus-ring rounded-full pl-1">
          <img src="/chickenbutt-logo.svg" alt="ChickenButt logo" className="w-7 h-7 rounded-lg" />
          <span className="brand-wordmark text-[14px] tracking-tight">ChickenButt</span>
        </a>
        <nav className="hidden md:flex items-center gap-6 text-[13px] font-medium text-(--ink-dim)">
          <a href="#top" onClick={(e) => handleNavClick(e, 'top')} className="hover:text-(--ink) transition focus-ring rounded">Home</a>
          <a href="#name" onClick={(e) => handleNavClick(e, 'name')} className="hover:text-(--ink) transition focus-ring rounded">About</a>
          <a href="#features" onClick={(e) => handleNavClick(e, 'features')} className="hover:text-(--ink) transition focus-ring rounded">Features</a>
          <a href="#install" onClick={(e) => handleNavClick(e, 'install')} className="hover:text-(--ink) transition focus-ring rounded">Install</a>
          <a href="#contribute" onClick={(e) => handleNavClick(e, 'contribute')} className="hover:text-(--ink) transition focus-ring rounded">Contribute</a>
          <a href="#styleguide" onClick={(e) => handleNavClick(e, 'styleguide')} className="text-(--green-300) hover:text-(--green-400) transition focus-ring rounded flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-(--green-400)"></span>
            Style Guide
          </a>
        </nav>
        <div className="flex items-center gap-3">
          <a
            href="https://github.com/scottonanski/ChickenButt"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-outline px-3 py-1.5 text-[13px] flex items-center gap-2 focus-ring rounded-full"
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
            </svg>
            <span className="hidden sm:inline">GitHub</span>
          </a>

          {/* Mobile Menu Toggle */}
          <button
            type="button"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden! btn-outline p-2 text-(--ink-dim) hover:text-(--ink) focus-ring rounded-full"
            aria-label="Toggle navigation menu"
            aria-expanded={isMobileMenuOpen}
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Navigation Drawer */}
      {isMobileMenuOpen && (
        <div className="pointer-events-auto mt-2 w-full max-w-6xl card p-5 bg-(--bg)/95 backdrop-blur-xl border border-(--border-soft) flex flex-col gap-4 text-[14px] font-medium shadow-2xl md:hidden animate-in fade-in slide-in-from-top-2 rounded-2xl">
          <a href="#top" onClick={(e) => handleNavClick(e, 'top')} className="hover:text-(--orange-hi) transition py-1">Home</a>
          <a href="#name" onClick={(e) => handleNavClick(e, 'name')} className="hover:text-(--orange-hi) transition py-1">About</a>
          <a href="#features" onClick={(e) => handleNavClick(e, 'features')} className="hover:text-(--orange-hi) transition py-1">Features</a>
          <a href="#install" onClick={(e) => handleNavClick(e, 'install')} className="hover:text-(--orange-hi) transition py-1">Install</a>
          <a href="#contribute" onClick={(e) => handleNavClick(e, 'contribute')} className="hover:text-(--orange-hi) transition py-1">Contribute</a>
          <a href="#styleguide" onClick={(e) => handleNavClick(e, 'styleguide')} className="text-(--green-300) hover:text-(--green-400) transition py-1 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-(--green-400)"></span>
            Style Guide
          </a>
        </div>
      )}
    </div>
  );
}

