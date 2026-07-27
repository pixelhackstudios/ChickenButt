import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Terminal,
  Sparkles,
  Check,
  ChevronDown,
  ArrowRight,
  AlertCircle,
  Info,
  CheckCircle2,
  Zap,
  Cpu,
  Layers,
  ArrowLeft,
  Settings,
  SlidersHorizontal,
  Download
} from "lucide-react";

const corePalette = [
  { role: 'Logo orange', hex: '#D35500', varName: '--orange-500', desc: 'Main identity & primary CTA' },
  { role: 'Logo yellow', hex: '#FFFF00', varName: '--yellow-400', desc: 'Dot, terminal prompt & focus rings' },
  { role: 'Primary green', hex: '#6CC43D', varName: '--green-400', desc: 'Doodles, secondary buttons & status' },
  { role: 'Main background', hex: '#0B1114', varName: '--ink-900', desc: 'Cool blue-green dark page background' },
  { role: 'Card background', hex: '#121B1F', varName: '--ink-800', desc: 'Standard component containers' },
  { role: 'Raised surface', hex: '#19262A', varName: '--ink-700', desc: 'Elevated popovers & focused cards' },
  { role: 'Border', hex: '#2B3B3F', varName: '--ink-500', desc: 'Dividers & container borders' },
  { role: 'Main text', hex: '#F4F7EE', varName: '--ink-50', desc: 'High-contrast readable headings & body' },
  { role: 'Muted text', hex: '#A9B8B3', varName: '--ink-200', desc: 'Subheadings, descriptions & metadata' },
];

const greenRamp = [
  { name: '--green-50', hex: '#F2FCEB' },
  { name: '--green-100', hex: '#DDF7CC' },
  { name: '--green-200', hex: '#BDEB9D' },
  { name: '--green-300', hex: '#95D964' },
  { name: '--green-400', hex: '#6CC43D', tag: 'Primary Green' },
  { name: '--green-500', hex: '#4FAE2A' },
  { name: '--green-600', hex: '#388C22' },
  { name: '--green-700', hex: '#2B6B20' },
  { name: '--green-800', hex: '#24551F' },
  { name: '--green-900', hex: '#1D451B' },
  { name: '--green-950', hex: '#0D2810' },
];

const yellowRamp = [
  { name: '--yellow-50', hex: '#FFFFF0' },
  { name: '--yellow-100', hex: '#FFFFC7' },
  { name: '--yellow-200', hex: '#FFFF8A' },
  { name: '--yellow-300', hex: '#FFFF45' },
  { name: '--yellow-400', hex: '#FFFF00', tag: 'Exact Logo Yellow' },
  { name: '--yellow-500', hex: '#F0DE00' },
  { name: '--yellow-600', hex: '#C9B600' },
  { name: '--yellow-700', hex: '#978500' },
];

const orangeRamp = [
  { name: '--orange-50', hex: '#FFF4EA' },
  { name: '--orange-100', hex: '#FFE1C8' },
  { name: '--orange-200', hex: '#FFC18E' },
  { name: '--orange-300', hex: '#FF984E' },
  { name: '--orange-400', hex: '#F4741F', tag: 'Hover State' },
  { name: '--orange-500', hex: '#D35500', tag: 'Exact Logo Orange' },
  { name: '--orange-600', hex: '#B64700' },
  { name: '--orange-700', hex: '#8E3500' },
  { name: '--orange-800', hex: '#682700' },
];

const inkRamp = [
  { name: '--ink-950', hex: '#070C0E' },
  { name: '--ink-900', hex: '#0B1114', tag: 'Page Background' },
  { name: '--ink-800', hex: '#121B1F', tag: 'Card Background' },
  { name: '--ink-700', hex: '#19262A', tag: 'Raised Surface' },
  { name: '--ink-600', hex: '#223136' },
  { name: '--ink-500', hex: '#2B3B3F', tag: 'Borders' },
  { name: '--ink-400', hex: '#53656A' },
  { name: '--ink-300', hex: '#7D8D90' },
  { name: '--ink-200', hex: '#A9B8B3', tag: 'Muted Text' },
  { name: '--ink-100', hex: '#D6DFDA' },
  { name: '--ink-50', hex: '#F4F7EE', tag: 'Main Text' },
];

const gradients = [
  { name: '--gradient-green', css: 'linear-gradient(135deg, #BDEB9D 0%, #6CC43D 52%, #2B6B20 100%)', label: 'Green Gradient' },
  { name: '--gradient-yellow', css: 'linear-gradient(135deg, #FFFF8A 0%, #FFFF00 58%, #F0DE00 100%)', label: 'Yellow Gradient' },
  { name: '--gradient-orange', css: 'linear-gradient(135deg, #FF984E 0%, #D35500 62%, #B64700 100%)', label: 'Orange Gradient' },
  { name: '--gradient-dark', css: 'linear-gradient(145deg, #19262A 0%, #0B1114 72%)', label: 'Dark Ink Gradient' },
];

export default function StyleGuide({ onBack }) {
  const [copied, setCopied] = useState(null);
  const [gpuEnabled, setGpuEnabled] = useState(true);
  const [peerSyncEnabled, setPeerSyncEnabled] = useState(false);
  const [selectedModel, setSelectedModel] = useState("llama3.2");
  const [inputValue, setInputValue] = useState("");

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(text);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <TooltipProvider>
      <div className="style-guide-view min-h-screen bg-(--bg) text-(--ink) antialiased pb-24">
        {/* Toast Notification */}
        {copied && (
          <div className="fixed bottom-6 right-6 z-50 bg-(--ink-700) border border-(--green-400) text-(--ink-50) px-4 py-2.5 rounded-lg shadow-xl text-sm font-mono flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2">
            <span className="w-2 h-2 rounded-full bg-(--green-400)"></span>
            <span>Copied <strong className="text-(--green-300)">{copied}</strong> to clipboard</span>
          </div>
        )}

        {/* Sticky Header Bar */}
        <header className="sticky top-0 z-40 border-b border-(--border-soft) bg-(--bg)">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 sm:gap-4 min-w-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (onBack) onBack();
                  else window.location.hash = '';
                }}
                className="gap-1.5 sm:gap-2 font-mono text-xs text-(--ink-dim) hover:text-(--ink) shrink-0"
              >
                <ArrowLeft data-icon="inline-start" className="size-3.5" />
                <span className="hidden sm:inline">Back to main site</span>
                <span className="sm:hidden">Back</span>
              </Button>
              <Separator orientation="vertical" className="h-4 hidden sm:block bg-(--border-soft)" />
              <div className="flex items-center gap-2 min-w-0">
                <img src="/chickenbutt-logo.svg" alt="ChickenButt logo" className="w-6 h-6 rounded shrink-0" />
                <span className="font-display font-semibold text-xs sm:text-base tracking-tight truncate">Design System & Component Library</span>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Badge variant="secondary" className="gap-1.5 hidden md:inline-flex bg-(--green-950) text-(--green-300) border-(--green-700)">
                <span className="w-1.5 h-1.5 rounded-full bg-(--green-400) animate-pulse"></span>
                Shadcn UI Base Nova
              </Badge>
            </div>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-6 pt-10 space-y-16">
          {/* Hero Banner */}
          <section className="card p-6 sm:p-8 relative overflow-hidden border-(--border-soft)">
            <div className="absolute -right-17 -bottom-13 sm:w-[18rem] sm:h-72 lg:w-96 lg:h-96 opacity-3 pointer-events-none select-none hidden sm:block">
              <img
                src="/doodles/chickenbutt-logo-1200x1200-white.svg"
                alt="ChickenButt logo watermark"
                className="w-full h-full object-contain"
              />
            </div>

            <div className="relative z-10 max-w-3xl space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="border-(--orange-500)/40 text-(--orange-300) bg-(--orange-800)/20">
                  <Sparkles className="size-3 text-(--orange-400) mr-1" /> Shadcn UI Integrated
                </Badge>
                <Badge variant="outline" className="border-(--green-500)/40 text-(--green-300) bg-(--green-950)">
                  <span className="w-1.5 h-1.5 rounded-full bg-(--green-400) mr-1"></span> Cool Blue-Green Ink System
                </Badge>
              </div>
              <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-(--ink-50)">
                Component System & Color Token Laboratory
              </h1>
              <p className="text-(--ink-200) text-base leading-relaxed">
                This style guide isn't part of the main app. It's simply a design system used to build the site. Feel free to grab a copy of it if you want. All components powered by <strong className="text-(--ink-50)">Shadcn UI (Base Nova style)</strong>, custom-themed with our exact logo orange (<code className="font-mono text-xs bg-(--ink-700) px-1.5 py-0.5 rounded border border-(--ink-500)">#D35500</code>), leaf green (<code className="font-mono text-xs bg-(--ink-700) px-1.5 py-0.5 rounded border border-(--ink-500)">#6CC43D</code>), and cool blue-green ink neutrals (<code className="font-mono text-xs bg-(--ink-700) px-1.5 py-0.5 rounded border border-(--ink-500)">#0B1114</code>).
              </p>
            </div>
          </section>

          {/* Main Navigation Tabs */}
          <Tabs defaultValue="colors" className="w-full">
            <TabsList className="grid grid-cols-2 w-full max-w-md bg-(--ink-800) border border-(--border-soft) p-1 rounded-xl">

              <TabsTrigger
                value="colors"
                className="font-mono text-xs gap-2 data-[state=active]:bg-(--ink-700) data-[state=active]:text-(--ink-50) data-[state=active]:ring-1 data-[state=active]:ring-(--ink-500) font-semibold transition"
              >
                <Sparkles className="size-3.5 text-(--brand-green)" />
                Color Token Swatches
              </TabsTrigger><TabsTrigger
                value="components"
                className="font-mono text-xs gap-2 data-[state=active]:bg-(--ink-700) data-[state=active]:text-(--ink-50) data-[state=active]:ring-1 data-[state=active]:ring-(--ink-500) font-semibold transition"
              >
                <Layers className="size-3.5 text-(--brand-orange)" />
                Shadcn Components
              </TabsTrigger>

            </TabsList>

            {/* TAB CONTENT 1: SHADCN COMPONENTS */}
            <TabsContent value="components" className="space-y-16 pt-8 outline-none">

              {/* 1. BUTTONS & ACTIONS */}
              <section className="space-y-6">
                <div className="flex items-center justify-between border-b border-(--border-soft) pb-4">
                  <div>
                    <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2.5">
                      <span className="w-3 h-3 rounded-full bg-(--orange-500)"></span>
                      Buttons & Action Primitives
                    </h2>
                    <p className="text-sm text-(--ink-200) mt-1">Shadcn <code className="font-mono text-xs text-(--orange-400)">Button</code> component variants, sizes, and icon placements.</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Button Variants */}
                  <Card className="p-6 space-y-4">
                    <CardHeader className="p-0 space-y-1">
                      <CardTitle className="text-base font-semibold">Button Variants</CardTitle>
                      <CardDescription>Semantic style variants mapped to brand tokens.</CardDescription>
                    </CardHeader>
                    <CardContent className="p-0 pt-2 flex flex-wrap items-center gap-3">
                      <Button variant="default">Primary Action</Button>
                      <Button variant="secondary">Secondary</Button>
                      <Button variant="outline">Outline</Button>
                      <Button variant="ghost">Ghost</Button>
                      <Button variant="destructive">Delete</Button>
                      <Button variant="link">Text Link</Button>
                    </CardContent>
                  </Card>

                  {/* Button Sizes & Icon Alignment */}
                  <Card className="p-6 space-y-4">
                    <CardHeader className="p-0 space-y-1">
                      <CardTitle className="text-base font-semibold">Sizes & Icons</CardTitle>
                      <CardDescription>Inline icon triggers with proper data-icon attributes.</CardDescription>
                    </CardHeader>
                    <CardContent className="p-0 pt-2 flex flex-wrap items-center gap-3">
                      <Button size="lg">
                        <Zap data-icon="inline-start" /> Run Model
                      </Button>
                      <Button size="default">
                        <Terminal data-icon="inline-start" /> Execute
                      </Button>
                      <Button size="sm" variant="secondary">
                        <Check data-icon="inline-start" /> Saved
                      </Button>
                      <Button size="xs" variant="outline">
                        Tag
                      </Button>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button size="icon" variant="outline">
                            <Settings className="size-4" />
                            <span className="sr-only">Settings</span>
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Open Settings Menu</TooltipContent>
                      </Tooltip>
                    </CardContent>
                  </Card>
                </div>
              </section>

              {/* 2. DATA DISPLAY & CARDS */}
              <section className="space-y-6">
                <div className="flex items-center justify-between border-b border-(--border-soft) pb-4">
                  <div>
                    <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2.5">
                      <span className="w-3 h-3 rounded-full bg-(--green-400)"></span>
                      Cards, Badges & Avatars
                    </h2>
                    <p className="text-sm text-(--ink-200) mt-1">Structured information containers and user status indicators.</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Full Card Composition */}
                  <Card className="md:col-span-2 flex flex-col justify-between">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <Badge variant="secondary" className="bg-(--green-950) text-(--green-300) border-(--green-700)">
                          Local Peer Sync
                        </Badge>
                        <span className="font-mono text-xs text-(--ink-400)">v2.4.0</span>
                      </div>
                      <CardTitle className="text-lg font-bold text-(--ink-50) mt-2">
                        ChickenButt Local Model Engine
                      </CardTitle>
                      <CardDescription className="text-sm text-(--ink-200)">
                        Zero-latency peer-to-peer web inference with hardware acceleration.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 font-mono text-xs">
                      <div className="p-3 rounded-lg bg-(--ink-900) border border-(--ink-500) space-y-1.5">
                        <div className="flex justify-between text-(--ink-200)">
                          <span>Active Model:</span>
                          <span className="text-(--yellow-400) font-semibold">Llama-3.2-3B-instruct</span>
                        </div>
                        <div className="flex justify-between text-(--ink-200)">
                          <span>Memory Usage:</span>
                          <span className="text-(--green-300)">1.8 GB / 8 GB VRAM</span>
                        </div>
                        <div className="flex justify-between text-(--ink-200)">
                          <span>Peer Connection:</span>
                          <span className="text-(--green-300)">100% Encrypted P2P</span>
                        </div>
                      </div>
                    </CardContent>
                    <CardFooter className="flex justify-between items-center border-t border-(--border-soft) pt-4">
                      <div className="flex items-center gap-2">
                        <Avatar className="size-7 border border-(--green-400)">
                          <AvatarImage src="/chickenbutt-logo.svg" alt="User avatar" />
                          <AvatarFallback className="bg-(--orange-500) text-black font-bold">CB</AvatarFallback>
                        </Avatar>
                        <span className="text-xs text-(--ink-200)">scott@node-01</span>
                      </div>
                      <Button size="sm" variant="default">
                        Launch Dashboard <ArrowRight data-icon="inline-end" />
                      </Button>
                    </CardFooter>
                  </Card>

                  {/* Badge & Avatar Showcase Card */}
                  <Card className="p-6 space-y-6">
                    <div>
                      <h3 className="font-display text-sm font-semibold text-(--ink-200) uppercase tracking-wider mb-3">
                        Badge Variants
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="default">Default Badge</Badge>
                        <Badge variant="secondary">Secondary Badge</Badge>
                        <Badge variant="outline">Outline Badge</Badge>
                        <Badge variant="destructive">Destructive</Badge>
                      </div>
                    </div>

                    <Separator />

                    <div>
                      <h3 className="font-display text-sm font-semibold text-(--ink-200) uppercase tracking-wider mb-3">
                        Avatar States
                      </h3>
                      <div className="flex items-center gap-3">
                        <Avatar className="size-10 border border-(--orange-500)">
                          <AvatarImage src="/chickenbutt-logo.svg" alt="ChickenButt logo" />
                          <AvatarFallback>CB</AvatarFallback>
                        </Avatar>
                        <Avatar className="size-10">
                          <AvatarFallback className="bg-(--green-400) text-black font-bold">
                            JS
                          </AvatarFallback>
                        </Avatar>
                        <Avatar className="size-10">
                          <AvatarFallback className="bg-(--ink-700) text-(--ink-200) border border-(--ink-500)">
                            AI
                          </AvatarFallback>
                        </Avatar>
                      </div>
                    </div>
                  </Card>
                </div>
              </section>

              {/* 3. FORM CONTROLS & INPUTS */}
              <section className="space-y-6">
                <div className="flex items-center justify-between border-b border-(--border-soft) pb-4">
                  <div>
                    <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2.5">
                      <span className="w-3 h-3 rounded-full bg-(--yellow-400)"></span>
                      Form Controls & Input Primitives
                    </h2>
                    <p className="text-sm text-(--ink-200) mt-1">Interactive input fields, select dropdowns, and switch toggles.</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Text Input */}
                  <Card className="p-6 space-y-4">
                    <div className="space-y-1.5">
                      <label htmlFor="model-prompt" className="text-xs font-mono text-(--ink-200) font-semibold flex items-center justify-between">
                        <span>Terminal Command Input</span>
                        <span className="text-(--yellow-400)">$</span>
                      </label>
                      <Input
                        id="model-prompt"
                        placeholder="chickenbutt run --model llama3.2"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        className="font-mono text-xs"
                      />
                      <p className="text-[11px] text-(--ink-400)">Enter CLI parameters or model prompt configuration.</p>
                    </div>
                  </Card>

                  {/* Select Dropdown */}
                  <Card className="p-6 space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-mono text-(--ink-200) font-semibold flex items-center gap-1.5">
                        <Cpu className="size-3.5 text-(--green-400)" />
                        <span>Select LLM Engine</span>
                      </label>
                      <Select value={selectedModel} onValueChange={setSelectedModel}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Choose LLM Model" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectLabel>Local Quantized Models</SelectLabel>
                            <SelectItem value="llama3.2">Llama 3.2 3B (Fast local)</SelectItem>
                            <SelectItem value="qwen2.5">Qwen 2.5 7B Instruct</SelectItem>
                            <SelectItem value="mistral">Mistral 7B v0.3</SelectItem>
                            <SelectItem value="phi4">Phi-4 Mini 3.8B</SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                      <p className="text-[11px] text-(--ink-400)">Selected: <strong className="text-(--green-300) font-mono">{selectedModel}</strong></p>
                    </div>
                  </Card>

                  {/* Switch Controls */}
                  <Card className="p-6 space-y-4">
                    <h3 className="font-display text-sm font-semibold text-(--ink-200) uppercase tracking-wider">
                      Hardware Toggles
                    </h3>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <span className="text-xs font-semibold text-(--ink-50)">WebGPU Acceleration</span>
                          <p className="text-[11px] text-(--ink-400)">Utilize browser GPU compute shaders</p>
                        </div>
                        <Switch checked={gpuEnabled} onCheckedChange={setGpuEnabled} />
                      </div>
                      <Separator />
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <span className="text-xs font-semibold text-(--ink-50)">Peer WebRTC Sync</span>
                          <p className="text-[11px] text-(--ink-400)">Share model weights across mesh network</p>
                        </div>
                        <Switch checked={peerSyncEnabled} onCheckedChange={setPeerSyncEnabled} />
                      </div>
                    </div>
                  </Card>
                </div>
              </section>

              {/* 4. OVERLAYS & FEEDBACK */}
              <section className="space-y-6">
                <div className="flex items-center justify-between border-b border-(--border-soft) pb-4">
                  <div>
                    <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2.5">
                      <span className="w-3 h-3 rounded-full bg-(--orange-400)"></span>
                      Overlays, Modals & Feedback
                    </h2>
                    <p className="text-sm text-(--ink-200) mt-1">Dialogs, alerts, tooltips, and loading skeletons.</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Dialog & Dropdown Menu Triggers */}
                  <Card className="p-6 space-y-6">
                    <div>
                      <h3 className="font-display text-sm font-semibold text-(--ink-200) uppercase tracking-wider mb-2">
                        Dialog Modal & Popovers
                      </h3>
                      <p className="text-xs text-(--ink-200) mb-4">Click to open accessible modal dialog or contextual dropdown.</p>

                      <div className="flex flex-wrap items-center gap-4">
                        {/* Dialog Trigger */}
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button variant="default" className="gap-2">
                              <SlidersHorizontal data-icon="inline-start" /> Open Config Dialog
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="bg-(--ink-800) border border-(--ink-500) text-(--ink-50)">
                            <DialogHeader>
                              <DialogTitle className="font-display text-lg text-(--ink-50)">
                                Configure Model Environment
                              </DialogTitle>
                              <DialogDescription className="text-xs text-(--ink-200)">
                                Adjust local context window size, thread allocation, and GPU offload layers.
                              </DialogDescription>
                            </DialogHeader>

                            <div className="space-y-4 py-2 font-mono text-xs">
                              <div className="space-y-1">
                                <label className="text-(--ink-200)">Context Window (Tokens)</label>
                                <Input defaultValue="8192" className="bg-(--ink-900) border-(--ink-500)" />
                              </div>
                              <div className="space-y-1">
                                <label className="text-(--ink-200)">Thread Count</label>
                                <Input defaultValue="8" className="bg-(--ink-900) border-(--ink-500)" />
                              </div>
                            </div>

                            <DialogFooter className="gap-2 border-t border-(--ink-500) pt-3">
                              <DialogClose asChild>
                                <Button variant="outline" size="sm">Cancel</Button>
                              </DialogClose>
                              <Button variant="default" size="sm">Save Configuration</Button>
                            </DialogFooter>
                          </DialogContent>
                        </Dialog>

                        {/* Dropdown Menu Trigger */}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="outline" className="gap-2">
                              <Settings className="size-4" /> Quick Actions <ChevronDown className="size-3.5 opacity-60" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent className="w-56 bg-(--ink-800) border border-(--ink-500) text-(--ink-50)">
                            <DropdownMenuLabel className="font-mono text-xs text-(--ink-200)">Actions</DropdownMenuLabel>
                            <DropdownMenuSeparator className="bg-(--ink-500)" />
                            <DropdownMenuGroup>
                              <DropdownMenuItem className="focus:bg-(--ink-700) focus:text-(--ink-50) cursor-pointer">
                                <Terminal className="size-4 mr-2 text-(--yellow-400)" />
                                <span>Copy CLI String</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem className="focus:bg-(--ink-700) focus:text-(--ink-50) cursor-pointer">
                                <Download className="size-4 mr-2 text-(--green-400)" />
                                <span>Export Config JSON</span>
                              </DropdownMenuItem>
                            </DropdownMenuGroup>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>

                    <Separator />

                    {/* Skeletons */}
                    <div>
                      <h3 className="font-display text-sm font-semibold text-(--ink-200) uppercase tracking-wider mb-3">
                        Loading Skeleton Placeholders
                      </h3>
                      <div className="flex items-center gap-4 p-4 rounded-lg bg-(--ink-900) border border-(--ink-500)">
                        <Skeleton className="size-10 rounded-full bg-(--ink-700) shrink-0" />
                        <div className="space-y-2 w-full">
                          <Skeleton className="h-4 w-3/4 bg-(--ink-700)" />
                          <Skeleton className="h-3 w-1/2 bg-(--ink-700)" />
                        </div>
                      </div>
                    </div>
                  </Card>

                  {/* Alerts */}
                  <Card className="p-6 space-y-4">
                    <h3 className="font-display text-sm font-semibold text-(--ink-200) uppercase tracking-wider mb-2">
                      Alert Banners & System Callouts
                    </h3>

                    {/* Standard Info Alert */}
                    <Alert className="bg-(--ink-900) border-(--ink-500) text-(--ink-50)">
                      <Info className="size-4 text-(--yellow-400)" />
                      <AlertTitle className="font-semibold text-xs text-(--yellow-300)">Local Privacy Guarantee</AlertTitle>
                      <AlertDescription className="text-xs text-(--ink-200) mt-0.5">
                        Your prompt data and model weights never leave your browser memory.
                      </AlertDescription>
                    </Alert>

                    {/* Green Success Alert */}
                    <Alert className="bg-(--green-950)/50 border-(--green-700) text-(--green-50)">
                      <CheckCircle2 className="size-4 text-(--green-400)" />
                      <AlertTitle className="font-semibold text-xs text-(--green-300)">Model Loaded Successfully</AlertTitle>
                      <AlertDescription className="text-xs text-(--green-100) mt-0.5">
                        Llama 3.2 3B initialized in 0.4s via WebGPU shaders.
                      </AlertDescription>
                    </Alert>

                    {/* Destructive Alert */}
                    <Alert variant="destructive" className="bg-(--orange-800)/20 border-red-500/40 text-red-200">
                      <AlertCircle className="size-4 text-red-400" />
                      <AlertTitle className="font-semibold text-xs text-red-300">VRAM Allocation Warning</AlertTitle>
                      <AlertDescription className="text-xs text-red-200/80 mt-0.5">
                        System VRAM is low. Consider lowering context size to prevent paging.
                      </AlertDescription>
                    </Alert>
                  </Card>
                </div>
              </section>
            </TabsContent>

            {/* TAB CONTENT 2: COLOR TOKEN SWATCHES */}
            <TabsContent value="colors" className="space-y-16 pt-8 outline-none">

              {/* 1. Core Palette Overview */}
              <section>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-(--orange-500)"></span>
                      Core Brand Swatches
                    </h2>
                    <p className="text-sm text-(--ink-200) mt-1">Primary identity colors and key application surface roles</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {corePalette.map((item) => (
                    <div
                      key={item.varName}
                      onClick={() => handleCopy(item.hex)}
                      className="card p-4 flex items-center gap-4 cursor-pointer hover:border-(--green-400) transition group"
                    >
                      <div
                        className="w-14 h-14 rounded-xl shrink-0 border border-white/10 shadow-inner flex items-center justify-center font-mono text-xs font-semibold"
                        style={{ backgroundColor: item.hex }}
                      >
                        <span className={['#FFFF00', '#F4F7EE', '#6CC43D'].includes(item.hex) ? 'text-black' : 'text-white'}>
                          {item.hex}
                        </span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-sm text-(--ink-50)">{item.role}</span>
                          <span className="text-[10px] font-mono text-(--ink-400) opacity-0 group-hover:opacity-100 transition">Copy</span>
                        </div>
                        <div className="font-mono text-xs text-(--green-300) mt-0.5">{item.varName}</div>
                        <div className="text-xs text-(--ink-200) truncate mt-1">{item.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* 2. Green Ramp */}
              <section>
                <div className="mb-6">
                  <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-(--green-400)"></span>
                    Green Ramp
                  </h2>
                  <p className="text-sm text-(--ink-200) mt-1">
                    Leaf green scale for secondary buttons, doodles, indicators, and component highlights.
                  </p>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-11 gap-2.5">
                  {greenRamp.map((swatch) => (
                    <div
                      key={swatch.name}
                      onClick={() => handleCopy(swatch.hex)}
                      className="card p-2.5 flex flex-col justify-between h-36 cursor-pointer hover:scale-[1.03] transition border-(--ink-500) hover:border-(--green-400) group"
                    >
                      <div
                        className="w-full h-16 rounded-lg border border-white/10 relative p-1.5 flex flex-col justify-between"
                        style={{ backgroundColor: swatch.hex }}
                      >
                        {swatch.tag && (
                          <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-black/70 text-white self-start">
                            {swatch.tag}
                          </span>
                        )}
                      </div>
                      <div className="mt-2 font-mono text-[11px] leading-tight">
                        <div className="font-semibold text-(--ink-50) truncate">{swatch.name.replace('--green-', '')}</div>
                        <div className="text-(--ink-200) mt-0.5 uppercase">{swatch.hex}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* 3. Yellow Ramp */}
              <section>
                <div className="mb-6">
                  <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-(--yellow-400)"></span>
                    Yellow Ramp
                  </h2>
                  <p className="text-sm text-(--ink-200) mt-1">
                    Exact logo yellow (<code className="font-mono text-xs text-(--yellow-300)">#FFFF00</code>), used for dots, focus rings, terminal prompts, and active status.
                  </p>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-3">
                  {yellowRamp.map((swatch) => (
                    <div
                      key={swatch.name}
                      onClick={() => handleCopy(swatch.hex)}
                      className="card p-3 flex flex-col justify-between h-36 cursor-pointer hover:scale-[1.03] transition border-(--ink-500) hover:border-(--yellow-400)"
                    >
                      <div
                        className="w-full h-16 rounded-lg border border-black/10 relative p-1.5 flex flex-col justify-between"
                        style={{ backgroundColor: swatch.hex }}
                      >
                        {swatch.tag && (
                          <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-black/75 text-yellow-300 font-semibold self-start">
                            {swatch.tag}
                          </span>
                        )}
                      </div>
                      <div className="mt-2 font-mono text-xs">
                        <div className="font-semibold text-(--ink-50)">{swatch.name.replace('--yellow-', '')}</div>
                        <div className="text-(--ink-200) uppercase text-[11px] mt-0.5">{swatch.hex}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* 4. Orange Ramp */}
              <section>
                <div className="mb-6">
                  <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-(--orange-500)"></span>
                    Orange Ramp
                  </h2>
                  <p className="text-sm text-(--ink-200) mt-1">
                    Logo orange (<code className="font-mono text-xs text-(--orange-400)">#D35500</code>) for primary CTAs and brand identity.
                  </p>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-3">
                  {orangeRamp.map((swatch) => (
                    <div
                      key={swatch.name}
                      onClick={() => handleCopy(swatch.hex)}
                      className="card p-3 flex flex-col justify-between h-36 cursor-pointer hover:scale-[1.03] transition border-(--ink-500) hover:border-(--orange-400)"
                    >
                      <div
                        className="w-full h-16 rounded-lg border border-white/10 relative p-1.5 flex flex-col justify-between"
                        style={{ backgroundColor: swatch.hex }}
                      >
                        {swatch.tag && (
                          <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-black/70 text-white font-semibold self-start">
                            {swatch.tag}
                          </span>
                        )}
                      </div>
                      <div className="mt-2 font-mono text-xs">
                        <div className="font-semibold text-(--ink-50)">{swatch.name.replace('--orange-', '')}</div>
                        <div className="text-(--ink-200) uppercase text-[11px] mt-0.5">{swatch.hex}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* 5. Dark Neutral Ramp */}
              <section>
                <div className="mb-6">
                  <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-(--ink-700) border border-(--ink-500)"></span>
                    Dark Neutral Ink Ramp
                  </h2>
                  <p className="text-sm text-(--ink-200) mt-1">
                    Cool blue-green dark neutral structural surfaces (<code className="font-mono text-xs text-(--ink-200)">#0B1114</code> background, <code className="font-mono text-xs text-(--ink-200)">#121B1F</code> cards).
                  </p>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-11 gap-2.5">
                  {inkRamp.map((swatch) => (
                    <div
                      key={swatch.name}
                      onClick={() => handleCopy(swatch.hex)}
                      className="card p-2.5 flex flex-col justify-between h-36 cursor-pointer hover:scale-[1.03] transition border-(--ink-500) hover:border-(--green-400)"
                    >
                      <div
                        className="w-full h-16 rounded-lg border border-white/10 relative p-1.5 flex flex-col justify-between shadow-inner"
                        style={{ backgroundColor: swatch.hex }}
                      >
                        {swatch.tag && (
                          <span className="text-[8px] font-mono px-1 py-0.5 rounded bg-black/80 text-white self-start">
                            {swatch.tag}
                          </span>
                        )}
                      </div>
                      <div className="mt-2 font-mono text-[11px]">
                        <div className="font-semibold text-(--ink-50)">{swatch.name.replace('--ink-', '')}</div>
                        <div className="text-(--ink-200) uppercase text-[10px] mt-0.5">{swatch.hex}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* 6. Gradients */}
              <section>
                <div className="mb-6">
                  <h2 className="font-display text-2xl font-semibold tracking-tight flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-linear-to-r from-green-400 via-yellow-400 to-orange-500"></span>
                    Brand Linear Gradients
                  </h2>
                  <p className="text-sm text-(--ink-200) mt-1">Linear gradients for banners, buttons, and background accents</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {gradients.map((g) => (
                    <div
                      key={g.name}
                      onClick={() => handleCopy(g.name)}
                      className="card p-4 cursor-pointer hover:border-(--green-400) transition group"
                    >
                      <div
                        className="w-full h-24 rounded-xl border border-white/10 mb-3 shadow-md"
                        style={{ background: g.css }}
                      ></div>
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-(--ink-50)">{g.label}</span>
                        <span className="text-[10px] font-mono text-(--green-300)">{g.name}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </TabsContent>
          </Tabs>
        </main>
      </div>
    </TooltipProvider>
  );
}
