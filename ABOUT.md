# CareThread

CareThread is a jurisdiction-aware care-continuity agent. It watches
clinical documentation for follow-up obligations that get recommended and
then quietly dropped — most commonly an incidental finding on imaging that
never makes it into the discharge paperwork — and keeps that obligation
alive as an auditable case until a clinician confirms it's actually been
resolved.

## The problem

A radiology report recommends a repeat scan in 6–12 months. The discharge
summary that follows doesn't mention it. Nobody is deliberately at fault —
the recommendation just didn't survive the handoff between systems and
visits. Months later, nobody is tracking whether that scan ever happened.

## What CareThread does

1. **Detects** unresolved follow-up recommendations in incoming clinical
   artifacts (radiology reports, discharge summaries, progress notes).
2. **Proposes** a CareThread — a persistent, trackable obligation — rather
   than letting the finding disappear once the encounter ends.
3. **Links** later evidence (a follow-up scan, a progress note mentioning
   pending imaging) back to the original obligation, scoped strictly to
   that one patient.
4. **Proposes** the next step — link evidence, escalate, extend the
   deadline, or close the thread — but never acts unilaterally.
5. **Requires clinician approval** for every consequential state change,
   and keeps a complete, provenance-linked audit trail of what happened
   and why.

## What it deliberately does not do

CareThread does not diagnose disease, determine malignancy, interpret
images automatically, message patients autonomously, or close a case on
its own. It coordinates follow-up based on clinician-authored evidence —
it's a memory and accountability layer for care obligations, not a
diagnostic tool.

## Current scope

The MVP focuses on one workflow end to end: incidental pulmonary nodule
follow-up. That scope was chosen deliberately — narrow enough to build and
demo convincingly, general enough that the same architecture (patient
memory → obligation tracking → evidence matching → bounded agent actions)
extends to other kinds of dropped follow-up later.

See `README.md` (local, untracked) for how to run the current build, and
`project.md` (local, untracked) for the full technical specification.
