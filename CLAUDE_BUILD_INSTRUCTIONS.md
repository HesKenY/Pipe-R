# Pipe-R — Claude Website Build Instructions

## What This Is
Pipe-R is Ken's personal command center — a sci-fi themed project orchestration tool. Currently a Node.js terminal app (hub.js, 2,969 LOC). This prompt instructs Claude to build a full visual web UI for it.

## Instructions for Claude (claude.ai)

Upload this entire zip to Claude and paste the following:

---

**Build a complete sci-fi themed web UI for Pipe-R — a project command center and AI agent orchestrator.**

This zip contains the working Node.js backend (hub.js, server.js). Your job is to create a stunning browser-based frontend.

### Design Theme: SCI-FI COMMAND DECK
This is not a generic dashboard. This is a **spacecraft command interface**. Think: Alien Isolation meets Bloomberg Terminal meets JARVIS.

### Visual Requirements:
- **Dark space theme**: Deep black (#08090d) with subtle blue nebula gradients
- **Accent colors**: Electric cyan (#00f0ff) primary, amber (#f0a030) warnings, neon green (#00ff88) success, coral (#ff4466) errors
- **Animated robot face**: Center of the dashboard — a pixel-art or SVG robot face that:
  - Blinks randomly (eyes close briefly every 3-8 seconds)
  - Changes expression based on system state (happy when all green, thinking when processing, surprised on errors)
  - Has subtle glow/pulse animation around it
  - Eyes track the mouse cursor slightly
  - Says random greetings in a speech bubble on load
- **Scan line effect**: Subtle horizontal scan line that moves down the screen slowly (CSS animation)
- **Glow effects**: Buttons and panels have soft neon glow on hover
- **Grid lines**: Faint grid overlay on the background (like a holographic display)
- **Typing effect**: Text that appears letter-by-letter for status messages
- **Sound-ready**: Add click handlers that could play sounds (no actual audio needed)

### Pages/Panels to Build:
1. **Command Deck (Home)** — The robot face centered, system status ring around it, 6 quick-action buttons arranged in a hexagonal pattern, activity ticker at bottom
2. **Mission Log (Projects)** — Project cards with holographic borders, git status indicators, LOC counts, health pulse dots. Click to expand details.
3. **AI Core** — Ollama model cards with status LEDs, deployed agents list, "Deploy Agent" button with dramatic animation
4. **Training Lab** — Dataset cards, model builder wizard, progress bars with glow
5. **Nav Computer (Git)** — Terminal-style git interface with green-on-black output
6. **Task Board** — Kanban columns with draggable cards (Backlog/Active/Review/Done), priority color strips on cards
7. **Search** — Full-screen search overlay with live results, keyboard shortcut (Ctrl+K)
8. **Business Intel** — Revenue chart (simple bar chart), patent status timeline, contact cards
9. **Activity Feed** — Real-time scrolling feed with color-coded entries, filter buttons
10. **Settings** — Toggle switches, input fields with glow focus effect
11. **Commander's Log** — Note cards in a stack layout, tags as colored pills

### Interactive Elements (BUTTONS):
- All navigation through **clickable buttons** — large, glowing, satisfying to press
- Hexagonal quick-launch buttons on the Command Deck
- Toggle switches for settings (not checkboxes)
- Card-based selection (click to select, glow border on active)
- Floating action button (bottom-right) for quick actions
- Breadcrumb navigation at top
- Sidebar with icon buttons (collapsible)

### The Robot Face (IMPORTANT):
Create an SVG or CSS-art robot face named "Pipe-R" that serves as the mascot/avatar:
- Rectangular head with rounded corners
- Two circular eyes with inner pupil dots
- Antenna on top with blinking light
- Small mouth that can change shape (smile, neutral, O-shape)
- Entire face has a subtle cyan glow
- Face lives in a circular viewport with a rotating ring around it (like a power indicator)
- Must have at least 4 expressions: normal, happy, thinking, alert
- Eyes should softly follow cursor position via JS mousemove

### Tech Requirements:
- **Single HTML file** with embedded CSS and JS
- Pure HTML + CSS + JS (no frameworks)
- CSS animations for all effects (scan lines, glow pulses, face expressions)
- CSS Grid for layout, Flexbox for components
- CSS custom properties for all colors
- Smooth transitions on everything (0.2-0.3s ease)
- localStorage for persisting notes, tasks, and settings
- Include sample data so it looks populated
- Mobile-responsive (stack panels vertically on small screens)
- Minimum 60fps animations

### Sample Data to Include:
- 6 projects with names, statuses, LOC counts
- 5 tasks across kanban columns
- 3 deployed AI agents
- 10 activity feed entries
- 5 commander's log notes
- Patent status: "Filed April 2026, Provisional"

Return the complete HTML file. Make it feel like sitting in the cockpit of a machine that builds other machines.

---

## Session Log
When done, create `.claude/SESSION_LOG.md` with: date, files built, design decisions, what's still needed, notes for next session. Be specific — my other AI (Claude Code) needs to pick up where you left off.

## Memory / Logs
- Keep runtime logs in .claude/logs/ 
- Keep repo navigation notes in .claude/MEMORY_INDEX.md 
- Keep the latest checkpoint summary in .claude/SESSION_LOG.md 

