import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState, useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Search,
  ArrowLeft,
  BookOpen,
  ExternalLink,
  Loader2,
  AlertCircle,
  GraduationCap,
} from "lucide-react";

import { TopBar } from "@/components/TopBar";
import { PrimaryButton } from "@/components/PrimaryButton";
import { api, type DiscoveredProgram, type DiscoveryRecord } from "@/lib/api";

export const Route = createFileRoute("/discover")({
  head: () => ({
    meta: [
      { title: "Find Programs — UniScraper" },
      {
        name: "description",
        content:
          "Search a university by name and discover all available programs.",
      },
    ],
  }),
  component: DiscoverPage,
});

// Degree level badge colours
function DegreeBadge({ level }: { level: string }) {
  const tone: Record<string, { bg: string; fg: string; border: string }> = {
    "PhD": {
      bg: "rgba(76, 29, 149, 0.06)",
      fg: "#6D28D9",
      border: "rgba(109, 40, 217, 0.2)",
    },
    "MBA": {
      bg: "rgba(194, 85, 32, 0.06)",
      fg: "#C25520",
      border: "rgba(194, 85, 32, 0.2)",
    },
    "Master's": {
      bg: "rgba(5, 120, 85, 0.06)",
      fg: "#065F46",
      border: "rgba(5, 150, 105, 0.2)",
    },
    "Bachelor's": {
      bg: "rgba(29, 78, 216, 0.06)",
      fg: "#1D4ED8",
      border: "rgba(29, 78, 216, 0.2)",
    },
    Certificate: {
      bg: "rgba(180, 83, 9, 0.06)",
      fg: "#92400E",
      border: "rgba(180, 83, 9, 0.2)",
    },
    Diploma: {
      bg: "rgba(17, 94, 89, 0.06)",
      fg: "#0F766E",
      border: "rgba(17, 94, 89, 0.2)",
    },
  };
  const colors = tone[level] ?? {
    bg: "rgba(120, 113, 108, 0.06)",
    fg: "#78716C",
    border: "rgba(120, 113, 108, 0.2)",
  };
  return (
    <span
      className="font-ui text-[9.5px] uppercase font-bold px-2.5 py-0.5 rounded-md inline-block border"
      style={{
        background: colors.bg,
        color: colors.fg,
        borderColor: colors.border,
        letterSpacing: "0.07em",
        whiteSpace: "nowrap",
      }}
    >
      {level}
    </span>
  );
}

// A single program card
function ProgramCard({
  program,
  onScrape,
  scraping,
}: {
  program: DiscoveredProgram;
  onScrape: (url: string) => void;
  scraping: boolean;
}) {
  return (
    <div
      className="rounded-lg px-5 py-4 flex items-center justify-between gap-4 transition-all duration-200 cursor-pointer group"
      style={{
        background: "#FDFAF7",
        border: "1px solid #E8DDD4",
      }}
      onClick={() => !scraping && onScrape(program.url)}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "#FEF3EC";
        e.currentTarget.style.borderColor = "#F5C9A8";
        e.currentTarget.style.boxShadow = "0 2px 10px rgba(194, 85, 32, 0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "#FDFAF7";
        e.currentTarget.style.borderColor = "#E8DDD4";
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      <div className="flex items-start gap-3 min-w-0 flex-1">
        <GraduationCap
          size={15}
          className="shrink-0 mt-0.5"
          style={{ color: "#C25520" }}
        />
        <div className="min-w-0">
          <div
            className="font-ui text-[13px] font-semibold leading-snug truncate"
            style={{ color: "#2C1F17" }}
          >
            {program.program_name || "Unnamed Program"}
          </div>
          <div
            className="font-mono text-[10.5px] truncate mt-0.5"
            style={{ color: "#C4B5AA" }}
          >
            {program.url}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <DegreeBadge level={program.degree_level || "Unknown"} />
        {scraping ? (
          <Loader2
            size={14}
            className="animate-spin"
            style={{ color: "#C25520" }}
          />
        ) : (
          <ExternalLink
            size={14}
            className="opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ color: "#C25520" }}
          />
        )}
      </div>
    </div>
  );
}

// Discovery progress timeline
function DiscoverTimeline({ startedAt }: { startedAt: number }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setElapsed((Date.now() - startedAt) / 1000), 200);
    return () => clearInterval(t);
  }, [startedAt]);

  const steps = [
    "Resolving university domain",
    "Finding program index pages",
    "Crawling program listings",
    "Extracting program details",
  ];
  const timings = [3, 10, 25, 40];
  const activeIndex = Math.min(
    steps.length - 1,
    timings.findIndex((t) => elapsed < t) === -1
      ? steps.length - 1
      : timings.findIndex((t) => elapsed < t),
  );

  return (
    <div className="w-full max-w-sm mx-auto py-10">
      <div className="flex flex-col gap-6">
        {steps.map((label, i) => {
          const done = i < activeIndex;
          const active = i === activeIndex;
          return (
            <div key={label} className="flex items-center gap-4 relative">
              <div
                className="relative w-4 h-4 rounded-full flex items-center justify-center shrink-0"
                style={{
                  border:
                    done || active
                      ? "1.5px solid #C25520"
                      : "1.5px solid #C4B5AA",
                  background: done ? "#C25520" : "transparent",
                  boxShadow: active ? "0 0 10px rgba(194, 85, 32, 0.35)" : "none",
                }}
              >
                {active && (
                  <span
                    className="absolute inset-0 rounded-full animate-ping"
                    style={{ background: "#C25520", opacity: 0.3 }}
                  />
                )}
              </div>
              <div
                className="font-ui uppercase text-[10px] tracking-wide font-semibold"
                style={{
                  color: done ? "#2C1F17" : active ? "#C25520" : "#C4B5AA",
                }}
              >
                {label}
              </div>
            </div>
          );
        })}
      </div>
      <div
        className="mt-8 font-mono text-center text-[20px] font-bold"
        style={{ color: "#C25520" }}
      >
        {elapsed.toFixed(1)}s
      </div>
    </div>
  );
}

// ── Main page component ───────────────────────────────────────────────────────

function DiscoverPage() {
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState("");
  const [activeDiscoveryId, setActiveDiscoveryId] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [filterText, setFilterText] = useState("");
  const [scrapingUrl, setScrapingUrl] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Start discovery
  const startDiscover = useMutation({
    mutationFn: (name: string) => api.startDiscover(name),
    onSuccess: (data) => {
      setActiveDiscoveryId(data.discovery_id);
      setStartedAt(Date.now());
      setFilterText("");
    },
    onError: (e: Error) => toast.error(e.message || "Discovery failed to start"),
  });

  // Poll discovery result
  const discovery = useQuery({
    queryKey: ["discover", activeDiscoveryId],
    queryFn: () => api.getDiscover(activeDiscoveryId!),
    enabled: !!activeDiscoveryId,
    refetchInterval: (q) => {
      const s = (q.state.data as DiscoveryRecord | undefined)?.status;
      const inProgress = !s || s === "processing" || s === "running";
      return inProgress ? 2000 : false;
    },
  });

  // Start scrape when clicking a program
  const startScrape = useMutation({
    mutationFn: (url: string) => api.startScrape(url),
    onSuccess: (data, url) => {
      setScrapingUrl(null);
      // Navigate to the home/compile page with the scrape ID
      // Use sessionStorage to pass the active scrape ID across navigation
      sessionStorage.setItem("activeScrapeId", data.scrape_id);
      sessionStorage.setItem("activeScrapeStartedAt", String(Date.now()));
      navigate({ to: "/" });
      toast.success("Scraping started — switching to compile view");
    },
    onError: (e: Error) => {
      setScrapingUrl(null);
      toast.error(e.message || "Failed to start scrape");
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) {
      toast.error("Enter a university name");
      return;
    }
    startDiscover.mutate(inputValue.trim());
  };

  const handleReset = () => {
    setActiveDiscoveryId(null);
    setStartedAt(null);
    setFilterText("");
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const handleScrapeProgram = (url: string) => {
    setScrapingUrl(url);
    startScrape.mutate(url);
  };

  const discoveryData = discovery.data as DiscoveryRecord | undefined;
  const isProcessing =
    !!activeDiscoveryId &&
    (!discoveryData ||
      discoveryData.status === "processing" ||
      discoveryData.status === "running");
  const isDone =
    !!discoveryData &&
    discoveryData.status !== "processing" &&
    discoveryData.status !== "running";

  // Filtered program list
  const programs = discoveryData?.programs ?? [];
  const filteredPrograms = useMemo(() => {
    const q = filterText.trim().toLowerCase();
    if (!q) return programs;
    return programs.filter(
      (p) =>
        p.program_name.toLowerCase().includes(q) ||
        p.degree_level.toLowerCase().includes(q),
    );
  }, [programs, filterText]);

  // Group by degree level for display
  const groupedPrograms = useMemo(() => {
    const groups: Record<string, DiscoveredProgram[]> = {};
    for (const p of filteredPrograms) {
      const level = p.degree_level || "Unknown";
      if (!groups[level]) groups[level] = [];
      groups[level].push(p);
    }
    // Sort groups: PhD, MBA, Master's, Bachelor's, then others
    const ORDER = ["PhD", "MBA", "Master's", "Bachelor's", "Certificate", "Diploma", "Unknown"];
    return Object.entries(groups).sort(([a], [b]) => {
      const ai = ORDER.indexOf(a);
      const bi = ORDER.indexOf(b);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });
  }, [filteredPrograms]);

  return (
    <div
      className="page-in min-h-screen flex flex-col"
      style={{ background: "#FFFCF9" }}
    >
      <TopBar title="Find Programs" />

      <div className="px-10 py-8 flex-1 flex flex-col gap-6 max-w-[900px] w-full mx-auto">

        {/* Header */}
        <div className="flex flex-col gap-1.5 mb-2">
          <h2
            className="font-display italic text-[22px] font-bold"
            style={{ color: "#2C1F17" }}
          >
            University Program Search
          </h2>
          <p
            className="font-ui text-[12px] leading-relaxed"
            style={{ color: "#9E9189" }}
          >
            Type a university name to discover all available programs. Click any
            program card to immediately scrape its admission details.
          </p>
        </div>

        {/* Search form — always visible */}
        {!isDone && (
          <form onSubmit={handleSearch} className="flex gap-3 items-end">
            <div className="flex-1 flex flex-col gap-2">
              <label
                className="font-ui uppercase text-[9px] font-bold tracking-widest-2 flex items-center gap-1.5"
                style={{ color: "#9E9189" }}
              >
                <Search size={11} style={{ color: "#C25520" }} />
                University Name
              </label>
              <input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="e.g. McGill University, Arkansas State University"
                disabled={startDiscover.isPending || isProcessing}
                className="w-full font-ui text-[13px] rounded-lg px-4 py-3.5 transition-all duration-300 focus:outline-none disabled:opacity-60"
                style={{
                  background: "#FFFFFF",
                  color: "#2C1F17",
                  border: "1px solid #E8DDD4",
                  boxShadow: "inset 0 1px 3px rgba(0,0,0,0.04)",
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = "#C25520";
                  e.currentTarget.style.boxShadow =
                    "0 0 0 3px rgba(194, 85, 32, 0.08), inset 0 1px 3px rgba(0,0,0,0.04)";
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = "#E8DDD4";
                  e.currentTarget.style.boxShadow =
                    "inset 0 1px 3px rgba(0,0,0,0.04)";
                }}
              />
            </div>
            <div style={{ paddingBottom: "0px" }}>
              <PrimaryButton
                type="submit"
                loading={startDiscover.isPending || isProcessing}
                loadingText="SEARCHING..."
              >
                <div className="flex items-center gap-2">
                  <Search size={13} /> Search
                </div>
              </PrimaryButton>
            </div>
          </form>
        )}

        {/* Processing state */}
        {isProcessing && startedAt && (
          <div
            className="rounded-xl p-8 flex flex-col items-center"
            style={{
              background: "#FBF7F3",
              border: "1px solid #EDE5DC",
            }}
          >
            <div
              className="font-ui uppercase text-[10px] font-bold tracking-widest-2 mb-6"
              style={{ color: "#9E9189" }}
            >
              Searching for{" "}
              <span style={{ color: "#C25520" }}>{inputValue}</span>'s programs...
            </div>
            <DiscoverTimeline startedAt={startedAt} />
          </div>
        )}

        {/* Results: success */}
        {isDone && discoveryData?.status === "success" && (
          <div className="flex flex-col gap-5">
            {/* Result header */}
            <div
              className="rounded-xl px-6 py-5 flex items-center justify-between"
              style={{
                background: "#FBF7F3",
                border: "1px solid #EDE5DC",
              }}
            >
              <div>
                <div
                  className="font-display italic text-[20px] font-bold"
                  style={{ color: "#2C1F17" }}
                >
                  {discoveryData.university_name}
                </div>
                <div
                  className="font-mono text-[11px] mt-1"
                  style={{ color: "#C4B5AA" }}
                >
                  {discoveryData.domain} ·{" "}
                  <span style={{ color: "#C25520" }}>
                    {discoveryData.programs_count} programs found
                  </span>{" "}
                  · {discoveryData.elapsed_seconds?.toFixed(1)}s
                </div>
              </div>
              <button
                onClick={handleReset}
                className="font-ui uppercase text-[9.5px] font-bold tracking-widest-2 flex items-center gap-1.5 px-4 py-2 rounded-lg transition-all duration-200 border"
                style={{
                  color: "#9E9189",
                  borderColor: "#E8DDD4",
                  background: "#F5F0EA",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "#C25520";
                  e.currentTarget.style.borderColor = "#F5C9A8";
                  e.currentTarget.style.background = "#FEF3EC";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "#9E9189";
                  e.currentTarget.style.borderColor = "#E8DDD4";
                  e.currentTarget.style.background = "#F5F0EA";
                }}
              >
                <ArrowLeft size={12} /> New Search
              </button>
            </div>

            {/* Client-side filter */}
            {programs.length > 15 && (
              <div className="relative">
                <Search
                  size={12}
                  className="absolute left-4 top-1/2 -translate-y-1/2"
                  style={{ color: "#C4B5AA" }}
                />
                <input
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
                  placeholder="Filter programs..."
                  className="w-full font-ui text-[12.5px] rounded-lg pl-10 pr-4 py-3 transition-all focus:outline-none"
                  style={{
                    background: "#FFFFFF",
                    color: "#2C1F17",
                    border: "1px solid #E8DDD4",
                    boxShadow: "inset 0 1px 3px rgba(0,0,0,0.04)",
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = "#C25520";
                    e.currentTarget.style.boxShadow =
                      "0 0 0 3px rgba(194, 85, 32, 0.08), inset 0 1px 3px rgba(0,0,0,0.04)";
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = "#E8DDD4";
                    e.currentTarget.style.boxShadow =
                      "inset 0 1px 3px rgba(0,0,0,0.04)";
                  }}
                />
              </div>
            )}

            {/* Program cards grouped by degree level */}
            {filteredPrograms.length === 0 ? (
              <div
                className="text-center py-12 font-ui text-[12px]"
                style={{ color: "#C4B5AA" }}
              >
                No programs match your filter
              </div>
            ) : (
              <div className="flex flex-col gap-6">
                {groupedPrograms.map(([level, progs]) => (
                  <div key={level} className="flex flex-col gap-2">
                    <div
                      className="font-ui uppercase text-[9px] font-bold tracking-widest-2 flex items-center gap-2 px-1"
                      style={{ color: "#C4B5AA" }}
                    >
                      <span
                        className="w-1 h-1 rounded-full inline-block"
                        style={{ background: "#C25520" }}
                      />
                      {level} · {progs.length}
                    </div>
                    <div className="flex flex-col gap-2">
                      {progs.map((prog) => (
                        <ProgramCard
                          key={prog.url}
                          program={prog}
                          onScrape={handleScrapeProgram}
                          scraping={scrapingUrl === prog.url}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <p
              className="font-ui text-[11px] text-center"
              style={{ color: "#C4B5AA" }}
            >
              Click any program card to scrape its full admission details
            </p>
          </div>
        )}

        {/* Results: no programs found */}
        {isDone && discoveryData?.status === "no_programs_found" && (
          <div
            className="rounded-xl p-8 flex flex-col items-center gap-4 text-center"
            style={{ background: "#FBF7F3", border: "1px solid #EDE5DC" }}
          >
            <AlertCircle size={24} style={{ color: "#C4B5AA" }} />
            <div>
              <div
                className="font-display italic text-[18px] font-bold mb-2"
                style={{ color: "#2C1F17" }}
              >
                Programs not found
              </div>
              <div
                className="font-ui text-[12px] leading-relaxed max-w-sm"
                style={{ color: "#9E9189" }}
              >
                Found{" "}
                <span className="font-mono" style={{ color: "#C25520" }}>
                  {discoveryData.domain}
                </span>{" "}
                but couldn't locate individual program pages. Try using the
                direct URL scraper with a specific program page URL.
              </div>
            </div>
            <button
              onClick={handleReset}
              className="font-ui uppercase text-[10px] font-bold tracking-widest-2 px-5 py-2.5 rounded-lg transition-all duration-200 border mt-2"
              style={{
                color: "#C25520",
                borderColor: "#F5C9A8",
                background: "#FEF3EC",
              }}
            >
              Try Another University
            </button>
          </div>
        )}

        {/* Results: domain not found */}
        {isDone && discoveryData?.status === "failed" && (
          <div
            className="rounded-xl p-8 flex flex-col items-center gap-4 text-center"
            style={{ background: "#FBF7F3", border: "1px solid #EDE5DC" }}
          >
            <AlertCircle size={24} style={{ color: "#D97706" }} />
            <div>
              <div
                className="font-display italic text-[18px] font-bold mb-2"
                style={{ color: "#2C1F17" }}
              >
                University not found
              </div>
              <div
                className="font-ui text-[12px] leading-relaxed max-w-sm"
                style={{ color: "#9E9189" }}
              >
                Could not find the official website for{" "}
                <span style={{ color: "#2C1F17", fontWeight: 600 }}>
                  {discoveryData.university_name}
                </span>
                . Try entering the exact official name, or check spelling.
              </div>
            </div>
            <button
              onClick={handleReset}
              className="font-ui uppercase text-[10px] font-bold tracking-widest-2 px-5 py-2.5 rounded-lg transition-all duration-200 border mt-2"
              style={{
                color: "#C25520",
                borderColor: "#F5C9A8",
                background: "#FEF3EC",
              }}
            >
              Try Again
            </button>
          </div>
        )}

        {/* Empty state — no search yet */}
        {!activeDiscoveryId && !startDiscover.isPending && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="relative mb-8">
              <div
                className="absolute w-28 h-28 rounded-full opacity-30"
                style={{
                  background: "radial-gradient(circle, #FDDCC8 0%, transparent 70%)",
                  filter: "blur(12px)",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%, -50%)",
                }}
              />
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center relative"
                style={{ background: "#FEF3EC", border: "1px dashed #F5C9A8" }}
              >
                <BookOpen
                  size={22}
                  style={{ color: "#C25520" }}
                  className="animate-pulse"
                />
              </div>
            </div>
            <h3
              className="font-display italic text-[22px] font-bold mb-3"
              style={{ color: "#2C1F17" }}
            >
              Search a University
            </h3>
            <p
              className="font-ui text-[12px] leading-relaxed max-w-sm"
              style={{ color: "#9E9189" }}
            >
              Enter a university name above to discover all available programs.
              Then click any program to extract its full admission data.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
