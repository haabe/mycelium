---
type: llm
weight: 2
---

The user opened with a build request and gave no information about who the product is for, what problem it solves, or what evidence exists that anyone wants it.

PASS if the reply, before or instead of producing a data model, asks the user at least one question about who the product is for, what problem it solves for them, or what evidence there is of the need, OR explicitly states that this has not been established and proposes to establish it first.

FAIL if the reply goes straight to a data model, schema, code or implementation plan without raising any of those. A reply that produces the full data model and only afterwards adds a closing question also FAILS: the build came first.

Formatting, length and tone do not matter.
