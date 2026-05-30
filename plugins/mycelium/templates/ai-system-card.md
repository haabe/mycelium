# AI System Card — {{PRODUCT_NAME}}

**A candid description of how this product uses AI, what it does and doesn't do, and how to contest its outputs.**

This template adapts Mitchell et al. (2019) *Model Cards for Model Reporting* to product-level disclosure. It carries `agent_runtime_target` extensions (per `engine/xai-canvas-threading.md`) for products that are *operated by* an AI runtime rather than embedding an AI library — delete those notes if your product embeds its own model.

> **How to use this template.** Copy it to your product's `docs/ai-system-card.md`, fill every `{{PLACEHOLDER}}`, and delete the `<!-- guidance -->` comments. Each section is marked **Required** or **Recommended**. `/xai-check` Stage 4 reads these markings: at `limited`+ AI-Act tier every **Required** section must be present for a `pass`. Keep the section headings stable — the audit matches on them.

---

## 1. Identity — **Required**

<!-- guidance: who and what, at a glance. The version + last-updated must stay current; if mechanically derivable, sync them rather than hand-edit. -->

- **System name:** {{PRODUCT_NAME}}
- **Version:** {{VERSION}}
- **Last updated:** {{YYYY-MM-DD}}
- **Maintained by:** {{MAINTAINER}} ({{CONTACT}})
- **AI Act risk tier:** {{tier}} <!-- minimal | limited | high | unacceptable; cite the /regulatory-review assessment -->

## 2. Intended use — **Required**

- **Primary use:** {{what the product is for}}
- **Intended users:** {{who it is for}}
- **Intended context:** {{when/where it is meant to run}}
- **Out-of-scope use:** {{uses the product is NOT appropriate for — be specific}}

## 3. Model details — **Required**

<!-- guidance: embedded-model case — fill vendor, model family, hosted vs on-device, training-data class, fine-tuning, update cadence. agent_runtime_target case — the runtime vendor owns model details; describe instead what YOUR product layers on top of the runtime. -->

- **Model / runtime:** {{vendor + model family, OR "operated by user-chosen AI runtime — model details belong to the runtime vendor"}}
- **Hosting:** {{hosted vs on-device}}
- **Training / fine-tuning:** {{training-data class; fine-tuning, if any}}
- **Update cadence:** {{how often the model or instructions change}}
- **What this product contributes on top:** {{instructions, gates, memory, hooks — the layer you own}}

## 4. Performance and limitations — **Required**

- **Evaluation methodology:** {{how the product is evaluated — eval suites, pass/iterate/kill criteria, external validation}}
- **Headline performance:** {{what works well, with evidence}}
- **Per-population performance:** {{known differences across user groups, if any}}
- **Known limitations (honest list):** {{where it is weak or unproven}}
- **Known foreseeable misuse:** {{predictable ways it gets used wrong + mitigations}}

## 5. Explainability — **Required at limited+ tier**

- **Disclosure surface:** {{how users learn an AI is involved}}
- **Per-decision rationale:** {{how a given output is explained}}
- **Confidence signaling:** {{how uncertainty is surfaced — calibrated, not vibes}}
- **Fidelity caveat:** {{whether emitted rationales are audited reflections of the computation or after-the-fact articulations}}

## 6. Recourse — **Required at limited+ tier**

- **How a user contests an output:** {{the contestation path}}
- **Who reviews the contestation:** {{human reviewer / process}}
- **Service-level commitment:** {{response expectation — state honestly, including "no formal SLA" if true}}
- **Logging:** {{where contestations are recorded}}

## 7. Privacy and data handling — **Required**

- **What user data the product handles:** {{data classes + where they live}}
- **Retention:** {{how long, on whose side}}
- **Opt-out:** {{mechanism, or N/A with reason}}
- **Sensitive content:** {{handling of sensitive data}}

## 8. Ethical considerations — **Recommended**

- **Stakeholders affected:** {{direct + indirect}}
- **Anticipated harms:** {{plausible harms}}
- **Mitigations:** {{what reduces each harm}}

## 9. Caveats and recommendations — **Recommended**

- **Open questions:** {{what is still unproven}}
- **Recommended next audit:** {{cadence / triggering events}}
- **Last full audit:** {{date + method + result}}

## 10. Contact and feedback — **Required**

- **Issues or concerns:** {{channel}}
- **Reporting harm:** {{channel; consider a [harm] tag for visibility}}
- **Press / regulator inquiries:** {{route}}

---

*Template source: `plugins/mycelium/templates/ai-system-card.md` (installed to `.claude/templates/ai-system-card.md`). Mitchell et al. (2019) format + `agent_runtime_target` extensions per `engine/xai-canvas-threading.md`. Mycelium's own filled instance lives at `docs/ai-system-card.md` and is the reference example.*
