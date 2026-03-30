

# MCP-Healthcare: Clinical Decision Support MCP Server with Compliance Guardrails

## Overview
This specification defines a self‑contained Model Context Protocol (MCP) server that provides clinical decision support tools such as drug interaction checking, diagnostic criteria evaluation, and care pathway recommendations. The server runs entirely offline, enforces HIPAA‑compliant audit logging, and exposes its capabilities through a command‑line interface that can be invoked by existing Claude‑powered agents or other local services.

## Problem Statement
Healthcare environments often require clinical decision support that must operate without external network calls, guaranteeing data locality and HIPAA compliance while integrating with agent‑based AI workflows.

## Features
- **Drug Interaction Checker**: Evaluates a patient’s medication list against a curated interaction database and returns severity‑graded alerts (contraindication, warning, precaution).  
- **Diagnostic Criteria Evaluator**: Checks whether a set of clinical observations satisfies a selected diagnostic rule set (e.g., sepsis SIRS, COPD GOLD) and returns a boolean pass/fail with supporting evidence.  
- **Care Pathway Recommender**: Given a diagnosis and patient context, suggests an ordered set of care actions (medication, consult, monitoring) aligned with local guidelines.

## Tech Stack
- Python 3.11+ – core language  
- Click 8.1+ – CLI command parsing and sub‑command handling  
- Pydantic 2.6+ – data validation and settings management  
- SQLite3 – embedded relational database for audit logs and reference data  
- Pytest 8.0+ – test framework for unit and integration tests

## Quick Start / Installation
1. Clone the repository: `git clone https://github.com/your-org/mcp-healthcare.git`  
2. Create a virtual environment: `python -m venv venv` and activate it  
3. Install dependencies: `pip install -r requirements.txt`  
4. Initialize the database: `python -m mcp_healthcare.db init`  
5. Start the MCP server: `python -m mcp_healthcare.cli serve`

## Usage
- View CLI help: `python -m mcp_healthcare.cli --help`  
- Run a drug interaction check: `python -m mcp_healthcare.cli drug-check --patient-id 123`  
- Evaluate diagnostic criteria: `python -m mcp_healthcare.cli diag-eval --rule-set sepsis_sirs`  
- Get care pathway recommendations: `python -m mcp_healthcare.cli pathway-rec --diagnosis pneumonia`  
- Review audit logs: `python -m mcp_healthcare.cli audit-show`

## Architecture
The MCP‑Healthcare server follows a layered, click‑based architecture:
- **CLI Entrypoint**: Handles command‑line arguments and routes to sub‑commands (drug‑check, diag‑eval, pathway‑rec, audit‑show).  
- **Decision Core**: Contains the three feature modules—drug interaction checker, diagnostic criteria evaluator, and care pathway recommender—each exposing internal functions for the CLI layer.  
- **Storage Layer**: Manages SQLite database interactions, providing write‑ahead logging for HIPAA‑compliant audit and read‑only access to reference data (interaction tables, rule sets, pathway definitions).  
All components execute within a single OS process, with no threading and no external network calls, ensuring data locality and compliance.

## License
MIT License. See the `LICENSE` file for details.