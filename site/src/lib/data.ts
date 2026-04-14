import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const thisDir = dirname(fileURLToPath(import.meta.url));
const dataDir = resolve(thisDir, "../../public/data");

export type Confidence = "official" | "press_leak" | "analyst_estimate" | "derived";
export type Region = "global" | "japan" | "americas" | "emea" | "apac_ex_jp";
export type Generation = "last" | "current" | "pre_last";
export type FormFactor = "home" | "hybrid" | "handheld" | "pc_handheld";

export interface Fact {
  variant: string;
  region: Region;
  units_cumulative?: number | null;
  units_period?: number | null;
  period_start?: string | null;
  period_end: string;
  source_key: string;
  source_url: string;
  fetched_at: string;
  confidence: Confidence;
  note?: string;
}

export interface Console {
  slug: string;
  display_name: string;
  manufacturer: string;
  generation: Generation;
  form_factor: FormFactor;
  launch_date: string;
  variants: string[];
  notes?: string;
  wikipedia_article?: string;
  facts: Fact[];
}

export interface RegionLeader {
  console_slug: string;
  display_name: string;
  manufacturer: string;
  units_cumulative: number;
  period_end: string;
  source_key: string;
  source_url: string;
  confidence: Confidence;
}

export interface RegionEntry {
  slug: Region;
  display_name: string;
  description: string;
  leaderboard: RegionLeader[];
}

export interface Meta {
  schema_version: string;
  generated_at: string;
  total_consoles: number;
  total_facts: number;
  sources: { source_key: string; last_fetched_at: string }[];
}

function readJson<T>(name: string): T {
  try {
    return JSON.parse(readFileSync(resolve(dataDir, name), "utf8")) as T;
  } catch (e) {
    throw new Error(
      `Failed to read ${name} from ${dataDir}. Did you run \`python -m scrapers.normalize\`? Original: ${e}`,
    );
  }
}

export function loadConsoles(): Console[] {
  return readJson<{ consoles: Console[] }>("consoles.json").consoles;
}

export function loadRegions(): RegionEntry[] {
  return readJson<{ regions: RegionEntry[] }>("regions.json").regions;
}

export function loadMeta(): Meta {
  return readJson<Meta>("meta.json");
}

export function latestGlobalFact(console: Console): Fact | null {
  const globals = console.facts.filter((f) => f.region === "global" && f.units_cumulative != null);
  if (globals.length === 0) return null;
  return globals[0]; // already sorted newest-first by normalize.py
}

export function formatUnits(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return `${m.toFixed(m >= 100 ? 1 : 2)} M`;
  }
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)} K`;
  return n.toString();
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toISOString().slice(0, 10);
}

export function confidenceLabel(c: Confidence): string {
  switch (c) {
    case "official":
      return "Official";
    case "press_leak":
      return "Press leak";
    case "analyst_estimate":
      return "Analyst estimate";
    case "derived":
      return "Derived";
  }
}

export function sumGlobalByFamily(consoles: Console[]): number {
  let total = 0;
  for (const c of consoles) {
    const latest = latestGlobalFact(c);
    if (latest?.units_cumulative) total += latest.units_cumulative;
  }
  return total;
}

export function groupByGeneration(consoles: Console[]): Record<Generation, Console[]> {
  const out: Record<Generation, Console[]> = { current: [], last: [], pre_last: [] };
  for (const c of consoles) out[c.generation].push(c);
  return out;
}
