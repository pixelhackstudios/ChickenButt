import { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Hero from './components/Hero';
import TheName from './components/TheName';
import Features from './components/Features';
import Install from './components/Install';
import Contribute from './components/Contribute';
import Footer from './components/Footer';
import StyleGuide from './components/StyleGuide';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import Lenis from 'lenis';
import 'lenis/dist/lenis.css';

gsap.registerPlugin(ScrollTrigger);

export default function App() {
  const containerRef = useRef(null);
  const [currentHash, setCurrentHash] = useState(window.location.hash);

  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    });

    window.lenis = lenis;
    lenis.on('scroll', ScrollTrigger.update);

    const updateTicker = (time) => {
      lenis.raf(time * 1000);
    };

    gsap.ticker.add(updateTicker);
    gsap.ticker.lagSmoothing(0);

    return () => {
      gsap.ticker.remove(updateTicker);
      lenis.destroy();
      delete window.lenis;
    };
  }, []);

  useEffect(() => {
    const handleHashChange = () => {
      const newHash = window.location.hash;
      const wasStyleGuide = currentHash === '#styleguide' || currentHash === '#styling';
      const isStyleGuideNow = newHash === '#styleguide' || newHash === '#styling';

      setCurrentHash(newHash);

      // Only reset scroll position when toggling the StyleGuide view
      if (wasStyleGuide !== isStyleGuideNow) {
        if (window.lenis) {
          window.lenis.scrollTo(0, { immediate: true });
        } else {
          window.scrollTo(0, 0);
        }
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [currentHash]);

  const isStyleGuide = currentHash === '#styleguide' || currentHash === '#styling';

  useGSAP(() => {
    if (!isStyleGuide) {
      gsap.from('.hero-left-content > *', {
        opacity: 0,
        y: 30,
        duration: 0.8,
        stagger: 0.15,
        ease: 'power3.out',
      });

      gsap.from('.hero-right-content', {
        opacity: 0,
        scale: 0.8,
        duration: 1,
        ease: 'back.out(1.2)',
        delay: 0.3,
      });
    }
  }, { scope: containerRef, dependencies: [isStyleGuide] });

  if (isStyleGuide) {
    return <StyleGuide onBack={() => { window.location.hash = ''; }} />;
  }

  return (
    <div ref={containerRef} className="noise min-h-screen bg-(--bg) text-(--ink) antialiased selection:bg-(--orange) selection:text-[#160D06]">
      <Header />
      <main>
        <Hero />
        <TheName />
        <Features />
        <Install />
        <Contribute />
      </main>
      <Footer />
    </div>
  );
}
