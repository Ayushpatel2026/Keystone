# Keystone Documentation

This folder contains the LaTeX sources for all Keystone project documentation. Compiled PDFs live in [`../pdfs`](../pdfs).

## Contents

| Folder | Description |
| ------ | ----------- |
| [`ProblemStatementAndGoals/`](./ProblemStatementAndGoals) | The problem Keystone solves, its inputs and outputs, stakeholders, environment, and core and stretch goals. Also lists our custom documents. |
| [`DevelopmentPlan/`](./DevelopmentPlan) | Team processes: meeting and communication plans, roles, Git workflow and CI/CD, schedule, proof of concept plan, expected technology, AI use, coding standard, and team charter. |
| [`SRS/`](./SRS) | Software Requirements Specification: stakeholder, functional, non-functional, and data requirements, use cases, personas, and traceability. |
| [`HazardAnalysis/`](./HazardAnalysis) | Hazard analysis: FMEA, resulting safety and security requirements, and a roadmap for implementing them. |
| [`VnVPlan/`](./VnVPlan) | Verification and validation plan, including usability and deployment test procedures. |

## Shared Files

| File | Purpose |
| ---- | ------- |
| `Common.text` | Shared LaTeX macros, such as the project name and author list |
| `Comments.text` | Macros for template and reviewer comments |
| `Reflection.text` | Reflection prompts reused across deliverables |
| `SRS_Reflection.text` | Additional reflection questions for the SRS |

Shared bibliography entries are in [`../refs`](../refs).

## Building the Documents

Each deliverable folder contains a main `.tex` file named after the folder (e.g. `SRS/SRS.tex`). Documents are built automatically by GitHub Actions on every push and pull request. To build locally, run `pdflatex` and `bibtex` from inside the deliverable's folder.

## Conventions

- Requirements, hazards, and use cases use **descriptive IDs** (e.g. `FR_AssignTA`, `SSR_AuditLog`, `H_WrongRole`) instead of numbers.
- The Hazard Analysis links directly into the published SRS. When renaming an SRS requirement, update the matching `\srsref{...}` entries in `HazardAnalysis/`.
- Documentation PRs follow the review process in the Development Plan, and each deliverable is checked against the repo checklist and Avenue rubric before submission.