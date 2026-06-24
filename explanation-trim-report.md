# Explanation trim report

Review of all 85 `# Explanation` sections in `data/questions/active/`, looking for
text that can be cut without losing the actual reasoning.

> **Note on the append-only rule:** CLAUDE.md forbids *automation* silently
> bulk-rewriting items, but explicitly allows the user to edit one item
> deliberately. These trims should be done by hand (or via the in-app Edit
> dialog), not by a bulk script.

## The pattern

Most bloat is **Tutorials Dojo boilerplate** pasted in front of the real
reasoning: a generic "Service X is a fully managed service that lets you…"
paragraph (often re-expanding an acronym already defined in the question) before
the per-option rationale that's the only part worth keeping. A few also carry
paragraphs that are **irrelevant to the question itself**.

## Rule of thumb

- **Keep** every per-option rationale (the `1.` / `2.` / `3.` lines — that's the signal).
- **Keep** the one sentence that names the correct service and why it wins.
- **Cut** the generic service-definition lead-in paragraphs and filler.

## Worst offenders (highest payoff)

| File | Issue | Approx. trim |
|------|-------|------|
| **q-0062** | DynamoDB LSI — 6 paragraphs; LSI definition / "fetches" / projection concept restated 3–4× | ~70% |
| **q-0051** | DynamoDB LSI — "created with the table, can't add to existing" repeated 3× | ~50% |
| **q-0039** | Generic Inspector + ELB + Auto Scaling + Route 53 alias defs — 4 paragraphs before any option reasoning | ~60% |
| **q-0053** | The entire cache-hit-ratio paragraph is irrelevant to a field-level-encryption question | cut 1 paragraph |
| **q-0040** | AWS Config — two generic bulleted capability lists ("Evaluate…", aggregator sources) | ~50% |
| **q-0059** | CodePipeline `runOrder` — three worked numbering examples saying the same thing | ~40% |
| **q-0054** | SSL cert rules — keep the issuer table, drop the Match-Viewer worked example | ~30% |
| **q-0015** | ElastiCache — generic In-Memory store / Auto Discovery intro | ~40% |

## Other heavy intros worth trimming

- **q-0023 / q-0055** — near-duplicate Systems Manager Run Command intro paragraphs.
- **q-0058 / q-0078** — near-duplicate unified CloudWatch agent bullet lists.
- **q-0030** — Container Insights generic capability paragraphs.
- **q-0027** — Wavelength + EKS `aws-auth` ConfigMap walk-through; trim to the IAM-auth point.
- **q-0068** — Dedicated Hosts in Config — long generic "three reporting conditions" detail.
- **q-0080** — X-Ray Insights generic description.

## Recurring boilerplate to strip everywhere

- Generic service definitions: "X is just a / is simply / is primarily used to…"
  — q-0008, 0009, 0016, 0025, 0030, 0068, 0070, 0075, 0079, 0083.
- Acronyms re-expanded when already defined in the question/options
  (STS, ASG, AMI, OAI, …).
- Filler openers: "Take note that", "Keep in mind that", "Remember that",
  "In this scenario".
- Trailing throwaways: e.g. q-0023 "Run Command is offered at no additional cost."
