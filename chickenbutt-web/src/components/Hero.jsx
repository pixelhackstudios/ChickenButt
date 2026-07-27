export default function Hero() {
  const handleScrollTo = (e, targetId) => {
    e.preventDefault();
    if (window.lenis) {
      const element = document.getElementById(targetId);
      if (element) {
        window.lenis.scrollTo(element);
      }
    } else {
      const element = document.getElementById(targetId);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <section id="top" className="relative overflow-hidden">
      <div className="max-w-6xl mx-auto px-6 pt-28 sm:pt-40 pb-16 sm:pb-24 grid lg:grid-cols-[1.35fr_0.65fr] gap-10 items-center">
        <div className="hero-left-content">
          <div className="flex flex-wrap items-center gap-2 mb-7">
            <span className="badge">
              <span className="dot"></span>Local-first · GPL-3.0
            </span>
            <span className="badge">GTK4 + libadwaita</span>
            <span className="badge">runs on Ollama</span>
          </div>
          <h1 className="font-display text-[1.85rem] sm:text-[2.7rem] lg:text-[3rem] leading-[1.08] tracking-tight">
            <span className="text-gradient-green">Talk to</span> your <span className="text-gradient-green">local AI</span><br className="hidden sm:inline" />
            In a <span className="text-gradient-orange">real desktop app.</span>
          </h1>
          <p className="mt-6 text-base sm:text-lg text-(--ink-dim) max-w-xl leading-relaxed">
            ChickenButt is a native GNOME client for language models running on your own hardware.
            Streaming Markdown, syntax-highlighted code, conversation history that persists — and no
            account, no subscription, and no connection to anything but your own machine.
          </p>
          <div className="mt-8 sm:mt-9 flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5 sm:gap-4">
            <a href="#features" onClick={(e) => handleScrollTo(e, 'features')} className="btn-outline px-6 py-3.5 text-[15px] focus-ring text-center">See it strut</a>
            <a href="#install" onClick={(e) => handleScrollTo(e, 'install')} className="btn-primary px-6 py-3.5 text-[15px] focus-ring text-center">Get ChickenButt →</a>
          </div>
        </div>

        <div className="flex flex-col items-center justify-center hero-right-content mt-6 lg:mt-0">
          <div className="peck">
            <img
              src="/chickenbutt-mascot.svg"
              alt="ChickenButt mascot"
              className="w-72 h-72 sm:w-80 sm:h-80 lg:w-90 lg:h-90 rounded-[2.5rem]"
            />
          </div>
          <div className="w-72 sm:w-80 lg:w-90 bg-(--ink-800) backdrop-blur-sm border border-(--border-soft) rounded-xl px-4 py-3 text-xs sm:text-xs font-mono text-(--ink-dim) text-center shadow-lg -mt-14 relative z-10">
            The bubble is <span className="text-(--yellow-soft)">also</span>, technically, a butt.
          </div>
        </div>
      </div>
    </section>
  );
}
