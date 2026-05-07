---
id: 2026-04-macos-can-i-open
date: 2026-04
contributor: internal-dogfood
contributor_link: null
project: macos-can-i-open
mechanism_or_status: one-off
commits: []
subclass: null
---

# macos-can-i-open — what Mycelium improved

**Audience**: practitioners interested in what dogfood looks like on a native-platform project.
**Time to read**: 3 min.
**Last updated**: 2026-05-08.

## The project

A native macOS app for bulk file-type-association management. Swift / SwiftUI, LaunchServices, AXUIElement.

## What it taught the framework

Two reusable corrections worth keeping, both from observed agent failure, both now project-memory entries the agent will respect on the next macOS project:

1. **`@EnvironmentObject` is unsafe in SwiftUI Table cells.** SwiftUI Table cells lose `@EnvironmentObject` on scroll — the cells are recycled and the environment context goes with them. Use concrete passed values instead.
2. **`AXIsProcessTrusted()` lies for ad-hoc-signed apps.** It returns `true` even when the actual AX permission is missing, because the trust cache is stale or scoped incorrectly. Test by calling a real AX function and checking for the AX-not-permitted error code instead.

Both corrections are project-local. Neither has graduated to a framework-level mechanism because there is not yet a cluster of native-platform misuse patterns. If two more macOS projects produce similar OS-API-lies-to-callers shapes, the cluster is graduation-eligible.

## Why it stays on the receipts list

Non-software products and non-macOS practitioners read this and see: Mycelium's correction discipline isn't web-stack-only. The receipts logged here are platform-specific facts the agent now knows.
