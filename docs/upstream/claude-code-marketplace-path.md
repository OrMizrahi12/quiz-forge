# Draft issue for anthropics/claude-code (not filed)

**Title:** A project's directory marketplace (`"path": "./plugin"`) runs another project's plugin hooks

**Environment:** Claude Code 2.1.296, Linux. Two git folders, both trusted.

**What happens:** two projects declare a marketplace with the same name and a relative directory source. A session
started in the second project runs the plugin hooks from the first project's folder. The user-level marketplace
cache (`~/.claude/plugins/known_marketplaces.json`) keeps one absolute path per marketplace name.

**Reproduction:**
1. In folders `a` and `b`, put `.claude/settings.json`:
   `{"extraKnownMarketplaces": {"repro-mkt": {"source": {"source": "directory", "path": "./plugin"}}}, "enabledPlugins": {"demo@repro-mkt": true}}`
2. Give each folder a `plugin/` marketplace with a plugin `demo` whose `UserPromptSubmit` hook runs
   `echo hook from folder <a or b> >> /tmp/hook.log`.
3. Run `claude -p "Say ok"` in `a`, then in `b`.

**Expected:** `hook from folder a`, then `hook from folder b`.

**Actual:** `hook from folder a` twice. After the second run, the cache names `b/plugin`. A session in `a` would now
run `b`'s hooks.

**Why it matters:** a hook is a guardrail (PreToolUse deny rules). A copy of a repository, for example a second
checkout or a rehearsal copy, silently swaps which guard runs in the other checkouts.

**Suggestion:** resolve a relative directory source against each project's own folder, or warn when one marketplace
name points at two paths.
