# Keystone

**A capstone project discovery and management platform.**

Keystone gives students, supervisors, instructors, and TAs a single place to propose, discover, and manage capstone projects, from the first proposal through team formation and final project approval. It is designed for the McMaster Software Engineering (SE), Computer Science (CS), and Mechatronics (TRON) capstone courses, and is built to be configurable enough to be reused by other courses and universities.

## Developers
- Ayush Patel
- Andrew Habib
- Waqar Ul-Hassan
- Ahmed Rashrash

**Project Duration:** September 15 2026 – Present

## Project Overview

Capstone project and team selection currently happens across disconnected tools (email, MS Forms, Avenue to Learn, MS Teams, GitLab). This leads to:

- Inconsistent project descriptions that don't set expectations
- No visibility into which projects are open, taken, or unselected
- Difficulty finding compatible teammates
- Supervisors who know little about the students contacting them
- Repetitive manual review work for instructors, and records that drift out of date after approval

## Key Features (planned)

- Structured project proposal templates for supervisors and students
- Instructor review of proposals before projects are listed
- Searchable project catalog with live availability and supervisor capacity
- Student and team profiles, and team discovery
- Team applications with recorded supervisor/team agreement
- Team project approval with automated pre-checks (in-platform, external, or integrated mode)
- Course enrollment import (Avenue to Learn or file upload) and team composition validation/export
- Notifications, checklists, and course reference material
- Per-course feature configuration and role-based visibility (including scoped access for external supervisors)

## Current Status

**Documentation phase:** We are currently working on the project documentation (problem statement, development plan, SRS, hazard analysis, and verification and validation planning). **No application code has been written yet; code will come soon.**

## Repository Structure

```
Keystone/
├── README.md                  
├── LICENSE                    # MIT license
├── .github/                   # Issue templates and CI workflows
├── docs/                      # All project documentation (LaTeX sources)
│   ├── README.md
│   ├── ProblemStatementAndGoals/
│   ├── DevelopmentPlan/
│   ├── SRS/                   # Software Requirements Specification
│   ├── HazardAnalysis/        # Hazard Analysis (FMEA, safety/security requirements)
│   ├── VnVPlan/               # Verification and Validation Plan
│   ├── Comments.text          # Shared LaTeX comment macros
│   ├── Common.text            # Shared LaTeX macros (project name, authors)
│   └── Reflection.text        # Shared reflection prompts
├── pdfs/                      # Compiled PDFs of each deliverable
├── refs/                      # Shared bibliography (References.bib)
└── (src/ coming soon)         # Application code (React + FastAPI)
```

## Documentation

Compiled PDFs are available in [`pdfs/`](./pdfs). Source files and details on how the docs are organized are in [`docs/`](./docs).
The documentation for this project is updated on the project's [Github.io page](https://ayushpatel2026.github.io/Keystone/).

## Planned Tech Stack

React (TypeScript) · Python / FastAPI · PostgreSQL · Docker · GitHub Actions (CI) · pytest, Jest, Playwright · SonarQube

## License

This project is licensed under the [MIT License](./LICENSE).