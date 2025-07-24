# Repository Guidelines


## Goals for AI agents, models and tools
- This project aims to wrap the ps6000a API in a modern pythonic manner. It should be customer focused and always aim to help customers use their Pico harware to measure or solve real world applications.
- The ongoing mission is to allow access to the power and speed of the Pico C / dll based API for engineers that are using higher level languages such as python (which is the only language in the scope of this project).

## Project Structure
- **pypicosdk/**: Source package containing library modules like `base.py`, `ps6000a.py`, `constants.py`, and `pypicosdk.py`.
- **examples/**: Example scripts demonstrating usage of the library.
- **docs/**: MkDocs documentation, including reference material under `docs/docs` and configuration in `docs/mkdocs.yml`.
- **tests/**: Pytest unit tests.
- **build-tools/**: Helper scripts for development; `version_updater.py` synchronises version numbers.
- **raw_api_files/** & **api_docs/**: API headers and reference documentation from Pico Technology.

## Coding Style
- Python 3.10+ is required (see `pyproject.toml`).
- Use four spaces for indentation.
- Follow `snake_case` for functions and variables, and `PascalCase` for class names.
- Keep lines under 100 characters where possible.
- Include type hints for function arguments and return types.
- Write Google‑style docstrings (`Args:`, `Returns:` etc.).
- Constants are defined with `IntEnum` classes in `constants.py`.

## Testing
- Use `pytest` for running tests. Execute `pytest -q` from the project root to run the suite.

## Documentation
- Documentation is built with MkDocs using the *readthedocs* theme (`docs/mkdocs.yml`).
- Reference pages rely on docstrings pulled in with `mkdocstrings`.
- Keep examples concise and formatted with the same coding conventions as the library.

## Versioning
- Version information is stored in `version.py` (docs and package version variables) and `pypicosdk/version.py`.
- The `build-tools/version_updater.py` script updates version numbers across the project.

## Contribution Tips
- Add new features by extending the classes in `pypicosdk`. Use `_call_attr_function` to call underlying PicoSDK DLL functions.
- When adding new tests, place them in `tests/` following the existing pytest style.
- Keep commit messages short but descriptive.
