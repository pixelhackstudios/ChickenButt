export default function Contribute() {
  return (
    <section
      id="contribute"
      className="max-w-6xl mx-auto px-6 py-16 sm:py-24 border-t border-(--border-soft) relative"
    >
      {/* Background glow effects */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-87.5 sm:w-150 h-62.5 sm:h-100 bg-(--brand-orange) opacity-[0.035] blur-[140px] rounded-full pointer-events-none" />
      <div className="absolute bottom-10 right-1/4 w-62.5 sm:w-100 h-50 sm:h-75 bg-(--brand-green) opacity-[0.025] blur-[120px] rounded-full pointer-events-none" />

      {/* Grid container */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch relative z-10">

        {/* ──────────────────────────────────────────
            CARD 1 — Main Invitation
            Desktop: lg:col-span-7
        ────────────────────────────────────────── */}
        <div className="card p-6 sm:p-8 lg:p-10 shadow-2xl bg-linear-to-br from-(--ink-800) via-(--ink-900) to-(--ink-950) border border-(--border-soft) lg:col-span-7 flex flex-col justify-between min-h-105">
          <div className="relative z-10 max-w-2xl flex flex-col justify-between h-full">
            <div>
              {/* Badge */}
              <div className="flex items-center mb-4 sm:mb-6">
                <span className="badge">
                  <span className="dot-green"></span>
                  come make it weirder
                </span>
              </div>

              <h2 className="font-display text-2xl sm:text-4xl lg:text-5xl tracking-tight uppercase leading-[1.1] mb-6">
                <span className="block">
                  <span className="whitespace-nowrap">
                    IT'S <span className="text-gradient-orange">NOT</span>
                  </span>{" "}
                  <span className="text-gradient-orange">WRITTEN IN STONE.</span>
                </span>

                <span className="block">
                  <span className="whitespace-nowrap">
                    LET'S <span className="text-gradient-green">HACK</span>
                  </span>{" "}
                  <span className="text-gradient-green">ON THIS THING.</span>
                </span>
              </h2>

              {/* Subtitle */}
              <p className="text-lg sm:text-xl text-(--ink-50) font-medium leading-snug mb-4">
                ChickenButt is still becoming whatever it's going to become.
              </p>

              {/* Body Prose */}
              <p className="text-[14px] sm:text-[15px] text-(--ink-dim) leading-relaxed mb-6">
                Fix a bug. Suggest a feature. Tear apart a bad decision. Build something strange.
                There's no committee, no sacred roadmap, and no reason the best ideas have to come from me.
              </p>

              {/* Callout */}
              <p className="font-display text-base sm:text-lg text-(--ink-50) tracking-tight mb-8">
                WHO KNOWS WHERE THIS THING COULD GO?
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-3.5 mt-auto pt-4">
              <a
                href="https://github.com/scottonanski/ChickenButt"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary px-6 py-3.5 text-[15px] focus-ring text-center gap-2 group"
              >
                <span>View the repo</span>
                <span className="transition-transform group-hover:translate-x-0.5">&rarr;</span>
              </a>
              <a
                href="https://github.com/scottonanski/ChickenButt/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-outline bg-(--ink-950) hover:bg-(--ink-800) px-6 py-3.5 text-[15px] focus-ring text-center"
              >
                Open an issue
              </a>
            </div>
          </div>
        </div>

        {/* ──────────────────────────────────────────
            CARD 2 — BREAK IT BETTER (Sidebar)
            Desktop: lg:col-span-5
        ────────────────────────────────────────── */}
        <div className="card p-6 sm:p-8 lg:p-10 lg:col-span-5 flex flex-col justify-between">
          <div className="relative z-10 flex flex-col justify-between h-full">
            <div>
              <div className="flex items-center justify-between gap-2 h-7 mb-4 sm:mb-6">
                <div className="font-bold text-xs tracking-wider text-(--orange-hi) uppercase">
                  BREAK IT BETTER
                </div>
                <span className="badge">
                  <span className="dot-green"></span>
                  WAYS IN
                </span>
              </div>

              {/* Action List (10 Compact Bullets) */}
              <ul className="space-y-2 sm:space-y-2.5 m-0 p-0 list-none">
                {[
                  ['01', 'Fix a rough edge'],
                  ['02', 'Improve the docs or website'],
                  ['03', 'Clarify an instruction'],
                  ['04', 'Test another distro'],
                  ['05', 'Check accessibility'],
                  ['06', 'Polish the GTK interface'],
                  ['07', 'Submit better screenshots'],
                  ['08', 'Build a missing feature'],
                  ['09', 'Challenge a bad decision'],
                  ['10', 'Brainstorm something strange'],
                ].map(([num, text]) => (
                  <li key={num} className="flex items-center gap-3">
                    <span className="inline-flex size-5.5 shrink-0 items-center justify-center rounded-full border border-(--green-500)/40 bg-(--green-950)/60 font-mono text-[10px] font-bold text-(--green-300) opacity-50">
                      {num}
                    </span>
                    <span className="text-[13px] sm:text-[14px] text-(--ink-50) font-medium leading-tight">
                      {text}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-6 pt-4 border-t border-(--border-soft)">
              <a
                href="https://github.com/scottonanski/ChickenButt/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[13px] font-medium text-(--green-300) hover:text-(--green-400) flex items-center gap-1.5 transition-colors group"
              >
                <span>Find something to mess with</span>
                <span className="transition-transform group-hover:translate-x-0.5">&rarr;</span>
              </a>
            </div>
          </div>
        </div>

        {/* ──────────────────────────────────────────
            CARD 3 — DON'T RUIN THE GOOD PARTS (Bottom Bar)
            Desktop: lg:col-span-12
        ────────────────────────────────────────── */}
        <div className="card p-6 sm:p-7 relative overflow-hidden lg:col-span-12 flex flex-col lg:flex-row lg:items-center justify-between gap-6 lg:gap-8">
          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6 lg:gap-8 w-full">
            {/* Principles */}
            <div className="space-y-3.5 flex-1">
              <div className="font-bold text-xs tracking-wider text-(--orange-hi) uppercase">
                DON'T RUIN THE GOOD PARTS
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {[
                  'Keep it local',
                  'Keep it simple',
                  'Respect GNOME',
                  'No accounts',
                  'No telemetry',
                  'No clutter',
                ].map((principle) => (
                  <div key={principle} className="flex items-center gap-2.5">
                    <span className="dot-green shrink-0"></span>
                    <span className="text-[13px] sm:text-[14px] text-(--ink-50) font-medium sm:whitespace-nowrap">
                      {principle}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Closing block */}
            <div className="lg:border-l lg:border-(--border-soft) lg:pl-8 flex flex-col justify-center shrink-0">
              <p className="font-display text-base sm:text-lg text-(--ink-50) leading-tight mb-1 uppercase">
                WEIRD IS WELCOME.
              </p>
              <p className="font-display text-base sm:text-lg text-(--orange-hi) leading-tight uppercase">
                BLOAT ISN'T.
              </p>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
