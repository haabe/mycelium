---
description: Smoke-test skill that confirms the Mycelium plugin loaded correctly. Returns a deterministic marker string for plugin-shape validation. Not for end-user invocation in normal use.
---

# Ping (smoke-test only)

When invoked, respond with exactly this single line and nothing else:

```
MYCELIUM_PLUGIN_LOAD_OK_v0.20.0
```

This skill is here to confirm the plugin packaging works end-to-end (manifest → marketplace → install → namespaced invocation). It will be removed once the full skill set has migrated into the plugin and the plugin's own validation suite covers load-correctness.

For real Mycelium skills, see the parent `skills/` directory once migration completes.
