# Model Designer Spec

## Project Intent

The new deck build includes a `Model Designer` tool backed by BRAIN.

This tool is for defining the proprietary offline developer model that will be built by the deck and its agent squad. It is not a wrapper around a hosted system. It is the planning and dataset-definition layer for a new local-first model.

## Core Surfaces

- `BRAIN Controller` for indexed memory, branch search, and design retrieval
- `Ken AI Chat` for operator instruction, clarification, and training intent capture
- `Agent Squad` for build execution, dataset shaping, testing, and validation

Ken AI Chat should be able to pull BRAIN context directly into a live prompt so operator requests can turn into indexed, auditable model-building dialogue rather than free-form chat with no retrieval layer.

## Capability Envelope

The target model is designed to support:

- local-first execution
- full workstation file visibility
- tool execution
- shell execution
- source control awareness
- project planning
- memory logging
- dream synthesis
- branch-aware reasoning
- visual perception
- UI control scaffolding

## Permission Intent

The target model should support a `full-trust local mode` for the owner machine.

In that mode the model is expected to:

- read and write approved project files
- invoke local tools and scripts
- inspect logs and metrics
- use vision or screen-derived context
- coordinate an offline build squad

All such actions should be auditable through BRAIN-backed logging and design records.

## Build Phases

1. BRAIN ingest and retrieval
2. Ken AI chat memory logging
3. model-design blueprint capture
4. dataset curation from logs, memory, dreams, branch snapshots, and project artifacts
5. training specification and evaluation harness
6. local runtime shell inside the deck

## Required Outputs

Every model design should produce:

- mission statement
- capability list
- permission profile
- memory strategy
- dream strategy
- training sources
- evaluation goals
- runtime plan
- rollout risks
