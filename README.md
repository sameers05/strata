# Strata

A self-hosted hierarchical task management tool for organizing work as **Projects → Group-tasks → Tasks**, with notes and status tracking at every level.

## Overview

Strata is built for managing work that doesn't fit a flat to-do list — where projects break down into logical groupings of tasks, and each level of the hierarchy needs its own notes and status, independent of dates or deadlines.

**Hierarchy:**
```
Project
 └── Group-task
      └── Task
```

Every level (Project, Group-task, Task) supports:
- **Notes** — free-text field for context, decisions, or details
- **Status** — current state of that item

No planned/actual dates, due dates, or scheduling fields are part of the design — status and notes are the only tracked attributes.

## Tech Stack

- **Backend:** FastAPI
- **Data layer:** SQLModel (SQLAlchemy + Pydantic)
- **Database:** SQLite
- **Frontend:** HTMX + Jinja2 templates
- **Migrations:** Alembic
- **Deployment:** Podman (rootless), SQLite file on a mounted volume

## Development Approach

This project follows **Specification-Driven Development (SDD)** using [GitHub Spec-Kit](https://github.com/github/spec-kit) with Claude Code:

1. `/specify` — define feature behavior and requirements
2. `/plan` — generate a technical implementation plan against the chosen stack
3. `/tasks` — break the plan into discrete, ordered implementation tasks
4. Implementation loop — Claude Code executes tasks against the spec, reviewed incrementally

## My Development Environment

- **Remote host:** Fedora Server 44 (i5-10500T, 32GB RAM, 512GB SSD)
- **Client:** Windows 11 Pro
- **IDE:** PyCharm 2026.1.4 (JetBrains Gateway remote development)
- **Container runtime:** Podman (rootless)

## Project Status

🚧 **Planning phase** — specification and architecture being finalized. No code has been written yet.

## License

MIT
