import { CheckCircle2, Ghost, Code2, Cpu, MessageSquare, Zap, ShieldCheck } from 'lucide-react';

const featureHighlights = {
  overview: [
    { label: 'SIMPLE BY DEFAULT', items: [['A text box, immediately', 'Open and start talking.'], ['No interface obstacle course', 'Everything useful stays nearby.']] },
    { label: 'ZERO DISTRACTION', items: [['Clean conversation thread', 'No popups, ads, banners, or intrusive UI.'], ['Native GTK4 interface', 'Feels built-in to your Linux desktop.']] },
  ],
  simple: [
    { label: 'FAST WHERE IT MATTERS', items: [['Live streaming responses', 'Answers render smoothly as they arrive.'], ['Native desktop behavior', 'Quick to open. Easy to dismiss.']] },
    { label: 'CONVERSATION FLOW', items: [['Formatted Markdown output', 'Clean typography with crisp spacing.'], ['One-tap message copy', 'Copy responses with a single click.']] },
  ],
  code: [
    { label: 'syntax', items: [['Auto language detection', 'Python, JS, Rust, C++, Bash, HTML, CSS.'], ['Copy with one tap', 'Instantly copy code snippets.']] },
    { label: 'layout', items: [['Capped height blocks', 'Long code won\'t hijack scrolling.'], ['Expandable view', 'Toggle full height when needed.']] },
  ],
  models: [
    { label: 'OLLAMA ENGINE', items: [['Ollama engine integration', 'Connects directly to your local Ollama instance.'], ['Instant model switching', 'One click, mid-conversation.']] },
    { label: 'MODEL MANAGEMENT', items: [['Real-time pull bar', 'See download progress live.'], ['Cloud model proxy', 'Optionally proxy cloud models through Ollama.']] },
  ],
  history: [
    { label: 'privacy', items: [['100% local chat storage', 'Conversations stay on your machine.'], ['Auto-titled history', 'Named from the conversation.']] },
    { label: 'export', items: [['JSON & Markdown export', 'Take your conversations anywhere.'], ['Instant topic access', 'Jump back into any past conversation seamlessly.']] },
  ],
};

function FeatureCard({ groups, footerNote, icon: Icon = Ghost }) {
  return (
    <div className="card p-6 sm:p-8 flex flex-col justify-between">
      <div className="space-y-6 sm:space-y-8">
        {groups.map((group) => (
          <div key={group.label}>
            <div className="font-bold text-xs tracking-wider text-(--orange-hi) uppercase mb-3 sm:mb-4">
              {group.label}
            </div>
            <div className="space-y-3.5 sm:space-y-4">
              {group.items.map(([name, desc]) => (
                <div key={name} className="group cursor-default">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="dot-green shrink-0"></span>
                      <span className="text-(--ink-50) text-[14px] sm:text-[15px] font-medium leading-snug">
                        {name}
                      </span>
                    </div>
                    <CheckCircle2 className="w-4 h-4 text-(--green-300) opacity-70 shrink-0" />
                  </div>
                  {desc && (
                    <p className="pl-6 text-[12px] sm:text-[13px] text-(--ink-200) mt-0.5">
                      {desc}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 pt-6 border-t border-(--border-soft) flex items-center gap-3">
        <Icon className="w-5 h-5 text-(--ink-400) shrink-0" />
        <span className="text-[13px] text-(--ink-400)">
          {footerNote || 'Everything expected. Nothing bloated.'}
        </span>
      </div>
    </div>
  );
}


function FeatureSpacer({ doodle = "egg-triple-lg.svg" }) {
  return (
    <div className="my-10 sm:my-20 flex items-center justify-center gap-4 relative" aria-hidden="true">
      <div className="h-px flex-1 bg-linear-to-r from-transparent via-(--border-soft) to-transparent" />
      <div className="px-4 py-1.5 shadow-sm flex items-center justify-center">
        <img
          src={`/doodles/${doodle}`}
          alt=""
          className="h-6 sm:h-8 w-auto opacity-10 brightness-0 invert select-none pointer-events-none"
        />
      </div>
      <div className="h-px flex-1 bg-linear-to-r from-transparent via-(--border-soft) to-transparent" />
    </div>
  );
}

export default function Features() {
  return (
    <section
      id="features"
      className="max-w-6xl mx-auto px-6 py-10 sm:py-16 mt-6 sm:mt-10 border-t border-(--border-soft)"
    >
      {/* Feature 1: Overview & Screenshots */}
      <div id="screenshots" className="mb-12 sm:mb-16 scroll-mt-24 flex items-start justify-between gap-4">
        <div>
          <span className="badge mb-4">
            <span className="dot-green"></span>
            What it actually does
          </span>
          <h2 className="font-display text-3xl sm:text-5xl tracking-tight mt-4 uppercase leading-[1.1]">
            <span className="text-gradient-green">Things</span> a chat needs.<br />
            <span className="text-gradient-orange">Nothing</span> it doesn't.
          </h2>
          <p className="mt-4 sm:mt-5 text-(--ink-dim) text-base sm:text-lg leading-relaxed max-w-2xl">
            The first screen is a text box. Everything else is one click away, <br className="hidden sm:block" />
            and stays there until you reach for it.
          </p>
        </div>
        <span className="font-display text-6xl sm:text-8xl lg:text-9xl text-white opacity-[0.03] select-none pointer-events-none shrink-0 leading-none">
          01
        </span>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)] gap-6 lg:gap-12 items-center">
        {/* Welcome Screenshot Image */}
        <figure className="m-0">
          <div className="shot-frame rounded-2xl overflow-hidden bg-(--ink-800)">
            <img
              src="/screenshot-chat.png"
              alt="ChickenButt chat screen showing modern GNOME styling and initial prompt box"
              className="w-full h-auto block"
              loading="lazy"
            />
          </div>
        </figure>
        <FeatureCard groups={featureHighlights.overview} icon={MessageSquare} footerNote="Less interface. More conversation." />
      </div>

      {/* Spacer 1 */}
      <FeatureSpacer doodle="egg-triple-lg.svg" />

      {/* Feature 2: Easy to Use */}
      <div className="mb-12 sm:mb-16 flex items-start justify-between gap-4">
        <div>
          <span className="badge mb-4">
            <span className="dot-green"></span>
            Easy-peasy, lemon-squeezy!
          </span>
          <h2 className="font-display text-3xl sm:text-5xl tracking-tight mt-4 uppercase leading-[1.1]">
            <span className="text-gradient-green">SIMPLE</span> to Open<br />
            <span className="text-gradient-orange">&amp; EASY</span> to Use.
          </h2>
          <p className="mt-4 sm:mt-5 text-(--ink-dim) text-base sm:text-lg leading-relaxed max-w-2xl">
            There’s nothing mysterious here. No hidden menus. <br className="hidden sm:block" />
            Everything you need is visible or one click away.
          </p>
        </div>
        <span className="font-display text-6xl sm:text-8xl lg:text-9xl text-white opacity-[0.03] select-none pointer-events-none shrink-0 leading-none">
          02
        </span>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)] gap-6 lg:gap-12 items-center">
        <FeatureCard groups={featureHighlights.simple} icon={Zap} footerNote="Built specifically for Linux GTK4 & libadwaita desktop standard." />
        <figure className="m-0 order-first lg:order-last">
          <div className="shot-frame rounded-2xl overflow-hidden bg-(--ink-800)">
            <img
              src="/screenshot-welcome.png"
              alt="A ChickenButt response showing a live streaming conversation thread"
              className="w-full h-auto block"
              loading="lazy"
            />
          </div>
        </figure>
      </div>

      {/* Spacer 2 */}
      <FeatureSpacer doodle="egg-triple-lg.svg" />

      {/* Feature 3: Code Display */}
      <div className="mb-12 sm:mb-16 flex items-start justify-between gap-4">
        <div>
          <span className="badge mb-4">
            <span className="dot-green"></span>
            But wait! There's more!
          </span>
          <h2 className="font-display text-3xl sm:text-5xl tracking-tight mt-4 uppercase leading-[1.1]">
            <span className="text-gradient-green">Need code?</span><br />
            It handles <span className="text-gradient-orange">that too.</span>
          </h2>
          <p className="mt-4 sm:mt-5 text-(--ink-dim) text-base sm:text-lg leading-relaxed max-w-2xl">
            It displays full code blocks - ready to be expanded, copied, and pasted at the click of a button.
          </p>
        </div>
        <span className="font-display text-6xl sm:text-8xl lg:text-9xl text-white opacity-[0.03] select-none pointer-events-none shrink-0 leading-none">
          03
        </span>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)] gap-6 lg:gap-12 items-center">
        <figure className="m-0">
          <div className="shot-frame rounded-2xl overflow-hidden bg-(--ink-800)">
            <img
              src="/screenshot-code.png"
              alt="ChickenButt code formatting example with syntax highlighting"
              className="w-full h-auto block"
              loading="lazy"
            />
          </div>
        </figure>
        <FeatureCard groups={featureHighlights.code} icon={Code2} footerNote="Automatic syntax detection and seamless clipboard copy." />
      </div>

      {/* Spacer 3 */}
      <FeatureSpacer doodle="egg-triple-lg.svg" />

      {/* Feature 4: Model Swapping */}
      <div className="mb-12 sm:mb-16 flex items-start justify-between gap-4">
        <div>
          <span className="badge mb-4">
            <span className="dot-green"></span>
            Pick your brains!
          </span>
          <h2 className="font-display text-3xl sm:text-5xl tracking-tight mt-4 uppercase leading-[1.1]">
            <span className="text-gradient-green">Model</span> swapping<br /> <span className="text-gradient-orange"> On The Fly.</span>
          </h2>
          <p className="mt-4 sm:mt-5 text-(--ink-dim) text-base sm:text-lg leading-relaxed max-w-2xl">
            Switch between local and cloud models without<br className="hidden sm:block" />
            leaving the conversation or restarting the app.
          </p>
        </div>
        <span className="font-display text-6xl sm:text-8xl lg:text-9xl text-white opacity-[0.03] select-none pointer-events-none shrink-0 leading-none">
          04
        </span>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)] gap-6 lg:gap-12 items-center">
        <FeatureCard groups={featureHighlights.models} icon={Cpu} footerNote="Full Ollama API integration with local & cloud model pulling." />
        <figure className="m-0 order-first lg:order-last">
          <div className="shot-frame rounded-2xl overflow-hidden bg-(--ink-800)">
            <img
              src="/screenshot-model.png"
              alt="ChickenButt model selection menu showing local and cloud model choices"
              className="w-full h-auto block"
              loading="lazy"
            />
          </div>
        </figure>
      </div>

      {/* Spacer 4 */}
      <FeatureSpacer doodle="egg-triple-lg.svg" />

      {/* Feature 5: Conversation Management */}
      <div className="mb-12 sm:mb-16 flex items-start justify-between gap-4">
        <div>
          <span className="badge mb-4">
            <span className="dot-green"></span>
            Never forget your conversations
          </span>
          <h2 className="font-display text-3xl sm:text-5xl tracking-tight mt-4 uppercase leading-[1.1]">
            <span className="text-gradient-green">Every Chat</span> Right<br />
            Where <span className="text-gradient-orange">You Left It.</span>
          </h2>
          <p className="mt-4 sm:mt-5 text-(--ink-dim) text-base sm:text-lg leading-relaxed max-w-2xl">
            Conversations stay local, title themselves, and wait where you left them.
          </p>
        </div>
        <span className="font-display text-6xl sm:text-8xl lg:text-9xl text-white opacity-[0.03] select-none pointer-events-none shrink-0 leading-none">
          05
        </span>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)] gap-6 lg:gap-12 items-center">
        <figure className="m-0">
          <div className="shot-frame rounded-2xl overflow-hidden bg-(--ink-800)">
            <img
              src="/screenshot-multi-chats.png"
              alt="ChickenButt multi-conversation list sidebar view"
              className="w-full h-auto block"
              loading="lazy"
            />
          </div>
        </figure>
        <FeatureCard groups={featureHighlights.history} icon={ShieldCheck} footerNote="Zero external telemetry. No analytics, tracking, or remote logging." />
      </div>
    </section>
  );
}