# MCP-Healthcare: Clinical Decision Support MCP Server

A Python-based MCP server providing clinical decision support tools with HIPAA-compliant audit logging and compliance guardrails.

## Overview

MCP-Healthcare is a Clinical Decision Support (CDS) server that operates entirely offline with no external API calls. It provides healthcare professionals with evidence-based recommendations through three core decision support tools, all while maintaining strict HIPAA compliance through comprehensive audit logging.

## Technology Stack

- **Language**: Python 3.11+
- **CLI Framework**: Click
- **Data Validation**: Pydantic
- **Database**: SQLite3
- **Testing**: Pytest
- **Server Protocol**: Model Context Protocol (MCP)

## Features

### Core CDS Tools

1. **Drug Interaction Checker**
   - Identifies potential interactions between medications
   - Severity classification (minor, moderate, severe)
   - Evidence-based interaction database
   - Patient-specific contraindication screening

2. **Diagnostic Criteria Evaluator**
   - Evaluates patient presentations against diagnostic criteria
   - Evidence-based diagnosis support
   - Differential diagnosis generation
   - Severity and certainty scoring

3. **Care Pathway Recommender**
   - Evidence-based clinical pathway recommendations
   - Patient risk stratification
   - Treatment option recommendations
   - Outcome tracking and guideline alignment

### Compliance & Security

- **HIPAA Compliance**: Full audit trail of all CDS recommendations
- **Offline Operation**: No internet connectivity required
- **Single Process**: Lightweight, container-friendly execution
- **Local Data**: All data stored locally in SQLite3

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mcp-healthcare
```

2. Run the initialization script:
```bash
chmod +x init.sh
./init.sh
```

The init.sh script will:
- Create a Python virtual environment
- Install dependencies
- Set up default environment variables
- Create necessary directories
- Run smoke tests

### Manual Setup (Alternative)

If you prefer manual setup:

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
# Or: pip install click pydantic pytest

# Set environment variables
export MCP_DATA_DIR=./data
export MCP_DB_NAME=healthcare.db
export MCP_LOG_LEVEL=INFO
```

### Environment Variables

- `MCP_DATA_DIR`: Directory for data files (default: ./data)
- `MCP_DB_NAME`: SQLite database filename (default: healthcare.db)
- `MCP_LOG_LEVEL`: Logging level (default: INFO)
- `MCP_AUDIT_LOG`: Audit log file path (default: ./data/audit.log)

## Running the Application

### Start the MCP Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run the MCP server
mcp-healthcare serve
```

### Check Help

```bash
mcp-healthcare --help
```

### Run Drug Interaction Checker

```bash
mcp-healthcare drug-check --medications "aspirin,ibuprofen"
```

### Run Diagnostic Criteria Evaluator

```bash
mcp-healthcare diagnose --symptoms "fever,cough" --vitals "temp=101.5"
```

### Run Care Pathway Recommender

```bash
mcp-healthcare pathway --condition "diabetes" --patient-age 65
```

## Testing

Run the test suite:

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_drug_interaction.py

# Run with coverage
pytest --cov=src
```

## Project Structure

```
mcp-healthcare/
├── src/
│   └── mcp_healthcare/
│       ├── __init__.py
│       ├── cli.py              # Click CLI application
│       ├── models.py           # Pydantic models
│       ├── tools/
│       │   ├── drug_checker.py
│       │   ├── diagnostic_evaluator.py
│       │   └── pathway_recommender.py
│       ├── storage/
│       │   ├── database.py
│       │   └── audit_logger.py
│       └── compliance/
│           └── hipaa_guard.py
├── tests/
│   ├── conftest.py
│   ├── test_drug_interaction.py
│   ├── test_diagnostic_evaluator.py
│   └── test_pathway_recommender.py
├── data/
│   └── reference_data.json     # Clinical reference data
├── init.sh
├── README.md
├── pyproject.toml
├── requirements.txt
└── .gitignore
```

## Development

### Code Style

Follow PEP 8 standards. Use type hints throughout the codebase.

```bash
# Check code style
pylint src/

# Format code
black src/ tests/
```

### Database Migrations

Database schema is initialized automatically on first run. Reference data is seeded from `data/reference_data.json`.

## Compliance & Audit Logging

All CDS recommendations are logged with:
- Timestamp
- User/system identifier
- Input parameters
- Recommendation output
- Confidence/severity scores
- Clinical justification

Audit logs are stored in `data/audit.log` and are immutable.

## Clinical Disclaimer

MCP-Healthcare is designed as a decision support tool to assist healthcare professionals. It does not replace clinical judgment and should always be used in conjunction with professional medical expertise. All recommendations should be reviewed by qualified healthcare providers before clinical implementation.

## License

Proprietary - All rights reserved

## Support

For issues, feature requests, or questions, please contact the development team.
