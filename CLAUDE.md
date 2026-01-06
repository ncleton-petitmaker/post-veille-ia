# BMAD Method Configuration for Claude Code

## Project: Post Veille IA

This project uses the **BMAD Method v6** (Build More, Architect Dreams) for AI-driven agile development.

## Available Agents

Use the following slash commands to activate specialized agents:

### Core Agents
- `/pm` - Product Manager: PRD creation, requirements, user stories
- `/analyst` - Analyst: Research, brainstorming, market analysis
- `/architect` - Architect: System architecture, technical design
- `/dev` - Developer: Implementation, coding, debugging
- `/ux` - UX Designer: User experience, wireframes, prototypes
- `/sm` - Scrum Master: Sprint planning, ceremonies, impediments
- `/tea` - Test Architect: Test strategy, quality assurance
- `/tech-writer` - Technical Writer: Documentation

### Quick Commands
- `/workflow-init` or `/wi` - Initialize workflow and analyze project
- `/prd` or `/pr` - Create Product Requirements Document
- `/arch` - Create Architecture Document
- `/stories` or `/es` - Create Epics and User Stories

## Output Directories

- `_bmad-output/planning-artifacts/` - PRDs, Architecture docs, UX designs
- `_bmad-output/implementation-artifacts/` - Sprint docs, stories, implementation notes
- `docs/` - Long-term project documentation

## Workflow Phases

1. **Analysis** (Optional): Brainstorm, research, explore solutions
2. **Planning** (Required): Create PRD, tech specs
3. **Solutioning** (Required): Architecture, UX, technical approach
4. **Implementation** (Required): Story-driven development with validation

## Getting Started

1. Start with `/pm` to create your PRD
2. Use `/architect` for technical design
3. Switch to `/dev` for implementation
4. Use `/sm` for sprint management

## BMAD Method Files

All BMAD configuration files are in `_bmad/`:
- `_bmad/bmm/agents/` - Agent definitions
- `_bmad/bmm/workflows/` - Workflow definitions
- `_bmad/bmm/data/` - Templates and data files
