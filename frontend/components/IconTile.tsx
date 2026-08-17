import type { LucideIcon } from "lucide-react";

const TONE_STYLES: Record<string, string> = {
  teal: "bg-teal-50 text-teal-600",
  blue: "bg-blue-50 text-blue-600",
  amber: "bg-amber-50 text-amber-600",
  rose: "bg-rose-50 text-rose-600",
  violet: "bg-violet-50 text-violet-600",
  emerald: "bg-emerald-50 text-emerald-600",
  slate: "bg-slate-100 text-slate-600",
};

export type Tone = keyof typeof TONE_STYLES;

export default function IconTile({ icon: Icon, tone = "slate", size = 36 }: { icon: LucideIcon; tone?: Tone; size?: number }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-xl ${TONE_STYLES[tone]}`}
      style={{ width: size, height: size }}
    >
      <Icon size={size * 0.52} />
    </span>
  );
}

const FINDING_TONE: Record<string, Tone> = {
  PULMONARY_NODULE: "teal",
  AORTIC_ANEURYSM: "rose",
  THYROID_NODULE: "violet",
  RENAL_CYST: "emerald",
  LUMBAR_DEGENERATIVE_CHANGES: "amber",
};

export function toneForFinding(findingType?: string | null): Tone {
  if (!findingType) return "slate";
  return FINDING_TONE[findingType] ?? "teal";
}

const TITLE_TONE: [RegExp, Tone][] = [
  [/pulmonary|nodule.*lobe|lung/i, "teal"],
  [/aort|cardiac|heart/i, "rose"],
  [/thyroid/i, "violet"],
  [/renal|kidney/i, "emerald"],
  [/lumbar|spine|spinal/i, "amber"],
];

export function toneForTitle(title: string): Tone {
  for (const [re, tone] of TITLE_TONE) {
    if (re.test(title)) return tone;
  }
  return "blue";
}

const ARTIFACT_TONE: Record<string, Tone> = {
  RADIOLOGY_REPORT: "teal",
  DISCHARGE_SUMMARY: "amber",
  PROGRESS_NOTE: "violet",
  LAB_RESULT: "emerald",
  PATIENT_MESSAGE: "blue",
  IMAGE: "rose",
  SCHEDULING_NOTE: "blue",
};

export function toneForArtifact(artifactType: string): Tone {
  return ARTIFACT_TONE[artifactType] ?? "slate";
}
