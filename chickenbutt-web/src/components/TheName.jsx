export default function TheName() {
  return (
    <section
      id="name"
      className="max-w-6xl mx-auto px-6 py-14 sm:py-20 border-t border-(--border-soft)"
    >
      <div className="card p-6 sm:p-12 lg:p-14 relative overflow-hidden">
        <div className="relative grid lg:grid-cols-[1.4fr_0.6fr] gap-8 lg:gap-12 items-center z-10">
          <div>
            <span className="badge mb-5">An explanation, sort of?</span>
            <h2 className="font-display text-2xl sm:text-4xl tracking-tight mt-4 mb-6">
              Yes, it's called <span className="text-gradient-green">ChickenButt.</span>
            </h2>
            <p className="text-(--ink-dim) text-base leading-relaxed mb-4">
              The logo is a rooster beside a speech bubble. The speech bubble is also,
              structurally, a butt. This was not an accident.
            </p>
            <p className="text-(--ink-dim) text-base leading-relaxed">
              The project needed a name, and every serious-sounding option in this category is
              some arrangement of the same four words. ChickenButt is memorable, it made the
              developer laugh, and the software underneath it is built carefully. Those things
              are allowed to coexist.
            </p>
          </div>

          <div className="flex flex-col items-center gap-5">
            <img
              src="/doodles/chickenbutt-logo-1200x1200-white.svg"
              alt="The ChickenButt mascot: a rooster head beside a speech bubble"
              className="absolute -right-20 sm:-right-20 -top-30 w-60 sm:w-120 h-60 sm:h-120 opacity-1 pointer-events-none select-none"
            />
          </div>
        </div>
      </div>
    </section>
  );
}

