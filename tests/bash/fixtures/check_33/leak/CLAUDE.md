# Test Fixture CLAUDE.md (leak scenario)

This fixture intentionally leaks FixtureTestPersonA's name in public-visibility content. Check 33 must flag this leak when run with MYCELIUM_ATTRIBUTION_REGISTRY pointing at this directory's registry.yml.

Other content unrelated to attribution.
