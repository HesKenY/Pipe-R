---
name: UX Rules — Button-Driven, No Typing
description: All UIs must be button-driven. Ken is a non-coder — no typing required in hubs or dashboards.
type: feedback
originSessionId: c25daccd-a89c-4ade-896e-c5ad4a5ab41b
---
Everything must work through buttons, not typed commands. This applies to the terminal TUI (hub.js), web UI, and any agent interfaces.

**Why:** Ken explicitly identifies as a non-coder. The CLAUDE.md for ForgeAgent states: "The user is a non-coder — everything must work through buttons, no typing required in the hub."

**How to apply:** New features need buttons/menus. Don't add CLI flags or require typing code. Agent terminal CLI (where users type tasks) is the one exception — keep it polished but that's the designated typing interface.
