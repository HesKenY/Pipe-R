---
name: Nest Dependency Install Hook
description: During Nest instance generation, check for required runtime dependencies and offer to install any that are missing
type: project
originSessionId: 891a6368-8f63-421e-8316-f0c391967118
---
Bird's Nest Instance Builder should include a dependency-check + install hook as part of the wizard flow when generating a new CHERP instance.

**Why:** Customers/admins running the Nest wizard may not have Node.js (or other required runtimes) installed on their machine. Without this, generated instances fail silently at first launch and require manual troubleshooting. Catching it during generation turns a broken handoff into a one-click install.

**How to apply:**
- First dep to handle: Node.js. Check with `node --version`; if missing, prompt user and install (winget/brew/apt depending on platform).
- Pattern should be extensible — future deps (git, ollama, etc.) plug into the same check/install/confirm loop.
- Always ask permission before installing anything — Ken's rule: no silent system-level changes.
- Belongs in the Nest wizard flow, not CHERP runtime.
