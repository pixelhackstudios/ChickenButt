export default function Footer() {
  return (
    <footer className="border-t border-(--border-soft) bg-(--bg) mt-14 sm:mt-20">
      <div className="max-w-6xl mx-auto px-6 py-8 sm:py-12 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <img src="/chickenbutt-logo.svg" alt="ChickenButt logo" className="w-7 h-7 rounded-md shrink-0" />
          <div className="text-xs sm:text-sm text-(--ink-200)">
            ChickenButt ·{' '}
            <span className="text-(--ink-300)">
              built by{' '}
              <a
                href="https://www.scottonanski.com"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-(--ink-50) underline underline-offset-2 transition"
              >
                Scott O'Nanski
              </a>
              ,{' '}
              <a
                href="https://www.pixelhackstudios.com"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-(--ink-50) underline underline-offset-2 transition"
              >
                Pixelhack Studios
              </a>
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 sm:gap-5 text-xs sm:text-sm text-(--ink-200)">
          <a
            href="mailto:whatsup@chickenbutt.dev"
            className="hover:text-(--ink-50) transition focus-ring rounded py-1"
          >
            whatsup@chickenbutt.dev
          </a>
          <a
            href="#styleguide"
            className="text-(--green-300) hover:text-(--green-400) font-medium transition focus-ring rounded flex items-center gap-1.5 py-1"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-(--green-400)"></span>
            Style Guide
          </a>
          <a
            href="https://github.com/scottonanski/ChickenButt"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-(--ink-50) transition focus-ring rounded py-1"
          >
            GitHub
          </a>
          <span className="badge">GPL-3.0-or-later</span>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 pb-8 sm:pb-10 flex flex-col gap-2">
        <p className="text-[11px] sm:text-xs text-(--ink-300) leading-relaxed">
          Also the reference client for the{' '}
          <a
            href="https://pmm.lol"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-(--ink-200) transition focus-ring rounded underline underline-offset-2"
          >
            Persistent Mind Model
          </a>
          . Not required to use this app.
        </p>
        <p className="text-[11px] sm:text-xs text-(--ink-300)">
          Free software. Local models. The name was on purpose.
        </p>
      </div>
    </footer>
  );
}
