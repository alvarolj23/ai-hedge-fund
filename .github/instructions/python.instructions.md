---
applyTo: '**'
---

# Python virtual environment standards.

Always activate the virtual environment before executing any Python code.

# Python execution requirements

- Always activate the virtual environment first: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix/Linux)
- Never run Python scripts directly without activating the environment
- Ensure all Python dependencies are installed in the activated environment
- Verify environment activation before running tests, agents, or applications

# Environment setup

- Use pip for dependency management (see `requirements.txt` and `pyproject.toml`)
- Create virtual environment with: `python -m venv venv`
- Install dependencies with: `pip install -r requirements.txt`
- Activate with: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix/Linux)