const requirements = [
  { label: 'OS', value: 'Linux · GTK4 + libadwaita' },
  { label: 'Runtime', value: 'Python 3' },
  { label: 'Backend', value: 'Ollama' },
  { label: 'Optional', value: 'gir1.2-gtksource-5', note: 'richer syntax highlighting' },
];

const InstallerPanel = ({ num, title, path = "~", children }) => (
  <div className="overflow-hidden shadow-2xl rounded-xl border border-border bg-(--ink-950)">
    <div className="bg-(--ink-800) border-b border-(--ink-950) px-4 py-3 flex items-center justify-between select-none gap-3">
      <div className="flex items-center gap-3">
        <span className="inline-flex size-7 items-center justify-center rounded-[5px] border border-(--orange-500)/60 bg-(--orange-800)/20 font-mono text-xs font-bold text-(--orange-300) shrink-0">
          {num}
        </span>
        <span className="font-display text-sm tracking-tight text-(--heading) uppercase">
          {title}
        </span>
      </div>
      <div className="font-mono text-xs text-(--ink-300) bg-(--bg)/80 px-2.5 py-1 rounded border border-(--border-soft) shrink-0">
        {path}
      </div>
    </div>
    <div className="p-4 sm:p-5 font-mono text-[12px] sm:text-[13px] leading-relaxed sm:leading-loose text-(--ink-100) overflow-x-auto">
      {children}
    </div>
  </div>
);

export default function Install() {
  return (
    <section
      id="install"
      className="max-w-6xl mx-auto px-6 py-16 sm:py-24 border-t border-(--border-soft) relative"
    >
      {/* Background glow */}
      <div className="absolute top-20 left-1/4 w-75 sm:w-125 h-75 sm:h-125 bg-(--brand-orange) opacity-[0.02] blur-[120px] rounded-full pointer-events-none" />

      <div className="mb-12 sm:mb-16 flex items-center justify-between gap-4 relative z-10">
        <div className="max-w-2xl">
          <span className="badge mb-4">
            <span className="dot-green"></span>
            Getting started
          </span>
          <h2 className="font-display text-3xl sm:text-5xl tracking-tight mt-4 uppercase leading-[1.1]">
            <span className="text-gradient-green">Two installs.</span> <br />
            One Pull. <br />
            <span className="text-gradient-orange">Now get crackin'!</span>
          </h2>
          <p className="mt-4 sm:mt-5 text-(--ink-dim) text-base sm:text-lg leading-relaxed">
            Ollama runs the models. ChickenButt is the window you talk to them through.
          </p>
        </div>
        <img
          src="/doodles/egg-triple-cracked-lg.svg"
          alt=""
          className="h-20 sm:h-32 lg:h-36 w-auto opacity-[0.03] brightness-0 invert select-none pointer-events-none shrink-0 mr-6 sm:mr-12 lg:mr-16"
        />
      </div>

      <div className="grid lg:grid-cols-[320px_minmax(0,1fr)] gap-8 items-stretch relative z-10">
        {/* ---- Requirements (Left Rail) ---- */}
        <div className="order-last lg:order-first flex flex-col">
          <div className="card p-6 sm:p-7 shadow-xl bg-(--panel)/80 backdrop-blur-sm flex flex-col justify-between flex-1">
            <div>
              <span className="badge mb-6 self-start">
                <span className="dot-green"></span>
                What you'll need
              </span>
              <ul className="space-y-4 text-[13px] sm:text-[14px] m-0 p-0 list-none">
                {requirements.map((r, i) => (
                  <li
                    key={r.label}
                    className={
                      'flex items-start justify-between gap-3 ' +
                      (i < requirements.length - 1
                        ? 'border-b border-(--border-soft) pb-4'
                        : '')
                    }
                  >
                    <span className="text-(--ink-dim) shrink-0">{r.label}</span>
                    <span className="font-mono text-(--ink-50) text-right text-[12px] sm:text-[13px]">
                      {r.value}
                      {r.note && (
                        <span className="block text-(--ink-400) text-[10px] sm:text-[11px] mt-0.5 font-sans uppercase tracking-wider">
                          {r.note}
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-auto pt-6 border-t border-(--border-soft)">
              <div className="flex items-center gap-2 font-mono text-xs text-(--green-300) uppercase tracking-wider mb-1.5 font-semibold">
                <span className="w-2 h-2 rounded-full bg-(--green-400) shadow-[0_0_8px_var(--green-400)] shrink-0"></span>
                READY WHEN YOU ARE
              </div>
              <p className="text-[13px] text-(--ink-300) leading-relaxed">
                Open ChickenButt, choose the model, and start typing.
              </p>
            </div>
          </div>
        </div>

        {/* ---- Steps Installer Panels (Console Column) ---- */}
        <div className="relative space-y-6">
          {/* Step 1: Install Ollama */}
          <InstallerPanel num="01" title="Install Ollama" path="~">
            <div className="term-line break-all sm:break-normal">
              <span className="term-prompt">$ </span>
              curl -fsSL https://ollama.com/install.sh | sh
            </div>
          </InstallerPanel>

          {/* Step 2: Pull a model */}
          <InstallerPanel num="02" title="Pull a model" path="~">
            <div className="term-line">
              <span className="term-prompt">$ </span>ollama pull gemma4:latest
            </div>
          </InstallerPanel>

          {/* Step 3: Get ChickenButt (source / dev) */}
          <InstallerPanel num="03" title="Or run from source" path="~/ChickenButt">
            <div className="term-line break-all sm:break-normal text-(--ink-300) mb-1">
              Prefer Flatpak above for everyday use. Source is for hacking on ChickenButt.
            </div>
            <div className="term-line break-all sm:break-normal">
              <span className="term-prompt">$ </span>
              git clone https://github.com/pixelhackstudios/ChickenButt.git
            </div>
            <div className="term-line">
              <span className="term-prompt">$ </span>cd ChickenButt
            </div>
            <div className="term-line">
              <span className="term-prompt">$ </span>./run.sh
            </div>
          </InstallerPanel>
        </div>
      </div>

      <div className="mt-12 sm:mt-16 grid md:grid-cols-2 gap-6 relative z-10">
        {/* ---- Cloud models ---- */}
        <div className="card p-5 sm:p-7 relative overflow-hidden group hover:border-(--green-400) transition-colors duration-300 flex flex-col">
          <div
            className="absolute -right-20 -top-20 w-64 h-64 rounded-full pointer-events-none opacity-[0.05] group-hover:opacity-[0.15] transition-opacity duration-500"
            style={{ background: 'var(--gradient-green)' }}
          />
          <div className="relative z-10 flex flex-col h-full">
            <span className="badge mb-4 self-start">
              <span className="dot-green"></span>
              Optional
            </span>
            <h3 className="font-display text-lg sm:text-xl tracking-tight mb-3">
              <span className="text-[#D35500]">Want models too big for your GPU?</span>
            </h3>
            <p className="text-[13px] sm:text-[14px] text-(--ink-200) leading-relaxed mb-6 grow">
              Ollama can proxy large models through your local daemon. Sign in once, pull a model with the{' '}
              <span className="font-mono text-[12px] text-(--ink-100) bg-(--bg) px-1.5 py-0.5 rounded border border-(--border-soft)">:cloud</span> suffix, and it shows
              up in ChickenButt's model picker alongside everything else.
            </p>

            <div className="rounded-xl border border-border bg-(--ink-950) p-4 font-mono text-[12px] sm:text-[13px] leading-relaxed sm:leading-loose text-(--ink-100) mb-5 overflow-x-auto">
              <div className="term-line">
                <span className="term-prompt">$ </span>ollama signin
              </div>
              <div className="term-line">
                <span className="term-prompt">$ </span>ollama pull gemma4:cloud
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mt-auto">
              <p className="text-[12px] text-(--ink-400) max-w-50 leading-snug">
                Runs on Ollama's servers, not yours.
              </p>
              <a
                href="https://ollama.com/search?c=cloud"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[13px] font-medium text-(--green-300) hover:text-(--green-400) flex items-center gap-1 transition-colors"
              >
                Browse cloud models &rarr;
              </a>
            </div>
          </div>
        </div>

        {/* ---- Flatpak ---- */}
        <div className="card p-5 sm:p-7 flex flex-col bg-linear-to-br from-(--panel) to-(--bg)">
          <span className="badge mb-4 self-start">
            <span className="dot-green"></span>
            Live
          </span>
          <h3 className="font-display text-lg sm:text-xl tracking-tight mb-3">
            <span className="text-[#4FAE2A]">Flatpak is NOW LIVE!</span>
          </h3>
          <p className="text-[13px] sm:text-[14px] text-(--ink-200) leading-relaxed mb-5 grow">
            Grab the Linux Flatpak from GitHub Releases—one file, no source build. Install it
            with Flatpak on your system, keep Ollama running on the host, and ChickenButt will
            talk to it over the network. Flathub can wait; this is the supported download today.
          </p>

          <div className="rounded-xl border border-border bg-(--ink-950) p-4 font-mono text-[12px] sm:text-[13px] leading-relaxed sm:leading-loose text-(--ink-100) mb-5 overflow-x-auto">
            <div className="term-line break-all sm:break-normal">
              <span className="term-prompt">$ </span>
              flatpak install --user ChickenButt-*-x86_64.flatpak
            </div>
            <div className="term-line break-all sm:break-normal">
              <span className="term-prompt">$ </span>
              flatpak run io.github.pixelhackstudios.ChickenButt
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mt-auto">
            <p className="text-[12px] text-(--ink-400) max-w-55 leading-snug">
              Linux · x86_64 · requires Ollama on the host
            </p>
            <a
              href="https://github.com/pixelhackstudios/ChickenButt/releases/latest"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-outline-solid px-5 py-3 text-[14px] focus-ring w-full sm:w-auto group flex items-center justify-center gap-2 shrink-0"
            >
              Download Flatpak
              <span className="opacity-60 group-hover:opacity-100 transition-opacity">↓</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}