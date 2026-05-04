# AI System Card — [System / Service Name]

> **What this is.** A public-facing document describing the AI components in this product: what they do, what they don't, how to contest their outputs, and what to expect when they're wrong. Format adapted from Mitchell et al. (2019) "Model Cards for Model Reporting" with extensions for hosted-LLM products. Read by users, regulators, partners, journalists.
>
> **What this is not.** This is not a marketing page, a technical whitepaper, or a legal-compliance certificate. It's a candid description, including known limitations.
>
> **Replace every bracketed placeholder.** Sections marked **Required** must be filled before launch. Sections marked **Recommended** strengthen the card but are not blocking unless the product is High-risk under the EU AI Act.

---

## 1. Identity (Required)

- **System name:** [Product / feature name]
- **Version:** [Semantic version or release tag]
- **Last updated:** [YYYY-MM-DD — must be within 12 months of launch / re-audit]
- **Maintained by:** [Team or contact email — a real human, not a no-reply address]
- **AI Act risk tier:** [minimal | limited | high — link to /regulatory-review classification rationale]

## 2. Intended use (Required)

- **Primary use:** [One-paragraph description of what the AI does for users.]
- **Intended users:** [Who is supposed to use this — be specific. "End consumers in the EU" not "everyone".]
- **Intended context:** [Where in the user journey the AI fires. Example: "After a user submits a support request and before a human agent reviews it."]
- **Out-of-scope use:** [What this AI is *not* for. Example: "Not for medical, legal, or financial decisions."]

## 3. Model details (Required)

- **AI vendor and model family:** [e.g., Anthropic Claude 3.5 Sonnet, OpenAI GPT-4o, in-house fine-tuned LLaMA 3, custom XGBoost classifier.]
- **Hosted vs. on-device:** [Where the inference runs. Affects data flow.]
- **Training data class:** [If known — public web, licensed corpus, customer data with consent. If vendor-hosted: "Training data not disclosed by vendor."]
- **Fine-tuning / customization:** [System prompt-only? RAG? Fine-tuned on which dataset?]
- **Update cadence:** [How often the model or prompt is updated, and what the user-visible signal is.]

## 4. Performance and limitations (Required)

- **Evaluation methodology:** [Internal eval set, public benchmarks, both. Sample sizes. Reviewer blinding.]
- **Headline performance:** [Top-line metric on representative tasks. Be honest about gaps.]
- **Performance per population:** [If the system serves multiple populations — language, region, demographic — disaggregate where possible. Acknowledge gaps where measurement was infeasible.]
- **Known limitations:** [List the failure modes you've observed. Hallucinations, bias, context-length, latency, language-coverage. The honest list — not a marketing list.]
- **Known foreseeable misuse:** [What you've already seen people try to do that this system shouldn't be used for.]

## 5. Explainability (Required when AI Act tier is `limited` or higher)

- **Disclosure surface:** [Where users see "this is AI" — UI element, copy, screenshot if helpful.]
- **Per-decision rationale:** [Does the user see *why* the AI did what it did, in the moment of impact? Pointer to the explanation surface.]
- **Confidence signaling:** [If the model emits uncertainty, how is it shown to users? If it doesn't, say so.]
- **Fidelity caveat:** [If the AI generates rationales (chain-of-thought, "because" explanations), state honestly: those rationales are the model's articulation, not a guaranteed account of the actual computation. Lanham et al. (2023) — chain-of-thought faithfulness is not assumed.]

## 6. Recourse (Required when AI Act tier is `limited` or higher)

- **How a user contests an output:** [Step-by-step path. Should be reachable in ≤2 clicks/interactions from where the AI surfaced.]
- **Who reviews the contestation:** [A human role, not a chatbot.]
- **Service-level commitment:** [Response time SLA. "We will respond within X business days."]
- **Logging:** [Contestation events are logged for product learning. Reference the privacy section.]

## 7. Privacy and data handling (Required)

- **What user data is sent to the model:** [Inputs that leave the user's device or session.]
- **Retention:** [Vendor-side retention policy. Customer-side retention.]
- **Opt-out:** [If applicable, how a user prevents their data from being used for training or model improvement.]
- **Cross-reference:** [Link to your privacy notice or DPIA. The system card complements but does not replace those.]

## 8. Ethical considerations (Recommended)

- **Stakeholders affected:** [End users, affected non-users, regulators. Anyone the AI's output touches.]
- **Anticipated harms:** [What can go wrong. Distinguish low-probability/high-impact from common-but-tolerable.]
- **Mitigations:** [What you've built to reduce those harms. Be specific — "we have guardrails" is not specific.]

## 9. Caveats and recommendations (Recommended)

- **Open questions:** [What you don't know yet about this system's behavior in production.]
- **Recommended next audit:** [When this card should be re-reviewed — typically annually, or after any material model/prompt update.]

## 10. Contact and feedback (Required)

- **Issues or concerns:** [Real human-monitored channel — not a no-reply.]
- **Reporting harm:** [If users have experienced harm, where they go.]
- **Press / regulator inquiries:** [Separate channel if applicable.]

---

*Template source: Mitchell, Wu, Zaldivar, Barnes, Vasserman, Hutchinson, Spitzer, Raji, Gebru (2019), "Model Cards for Model Reporting." Extended with explainability and recourse sections per EU AI Act Art. 13/50 and Selbst & Barocas (2018). Maintained in `.claude/templates/ai-system-card.md` — copy to your product's docs (e.g., `docs/ai-system-card.md`) and fill in. Mycelium does not host this artifact; it lives wherever your product's public docs live.*
