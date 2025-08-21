# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fintself is an open-source collaborative bank transaction scraper for Chilean banks. It uses Playwright to automate browser interactions, extracts financial movements, and exports them in multiple formats (JSON, CSV, XLSX).

## Development Commands

### Setup
```bash
make install          # Install dependencies with uv
uv pip install -e .[dev]  # Alternative install command
```

### Dependency Management
Dependencies are managed with `uv`. Do not modify `pyproject.toml` manually to add packages.

- **Production dependencies** (required for end users):
  ```bash
  uv add <package-name>
  ```

- **Development dependencies** (only needed for development):
  ```bash
  uv add --dev <package-name>
  ```

### Code Quality
```bash
make format          # Format code with Ruff (includes fixing)
make lint           # Check code with Ruff (no fixes)
uv ruff format .    # Format code only
uv ruff check .     # Lint only
uv ruff check . --fix  # Lint with fixes
```

### Testing
```bash
make test           # Run pytest test suite
uv pytest          # Alternative test command
```

### Running Scripts
```bash
uv run <script_path>           # Run any Python script in the project
uv run tutorials/debug_scrapers.py    # Debug specific scrapers
uv run tutorials/run_all_scrapers_visible.py  # Run all scrapers in visible mode
```

### Cleanup
```bash
make clean          # Remove temporary files and caches
```

## Architecture Overview

### Core Components

- **Factory Pattern**: `fintself.scrapers.get_scraper()` is the main entry point that returns scraper instances by bank_id
- **Abstract Base Class**: All scrapers inherit from `BaseScraper` in `fintself/scrapers/base.py`
- **CLI Interface**: Built with Typer in `fintself/cli.py`, supports interactive and environment variable-based authentication
- **Data Models**: Uses Pydantic models (`MovementModel`) for type safety and validation
- **Debug System**: Built-in debugging saves screenshots and HTML when `debug_mode=True`

### Project Structure

```
fintself/
├── cli.py                    # Typer-based CLI interface
├── core/
│   ├── models.py            # Pydantic data models (MovementModel)
│   └── exceptions.py        # Custom exceptions hierarchy
├── scrapers/
│   ├── __init__.py          # Factory function and scraper registry
│   ├── base.py              # BaseScraper abstract class
│   └── cl/                  # Chile-specific scrapers
│       ├── santander.py
│       ├── banco_chile.py
│       └── cencosud.py
└── utils/
    ├── logging.py           # Loguru configuration
    ├── output.py            # Export functions (JSON/CSV/XLSX)
    └── parsers.py           # Data parsing utilities
```

### Scraper Implementation Pattern

Each scraper must:
1. Inherit from `BaseScraper`
2. Implement `_get_bank_id()` - returns unique bank identifier
3. Implement `_login()` - handles authentication using self.user/self.password
4. Implement `_scrape_movements()` - extracts data and returns `List[MovementModel]`
5. Be registered in `_SCRAPERS` dictionary in `scrapers/__init__.py`

### Authentication Flow

1. CLI checks environment variables: `{BANK_ID}_USER` and `{BANK_ID}_PASSWORD`
2. If not found, prompts interactively (using getpass for passwords)
3. Credentials passed to scraper instance via `scrape(user, password)` method

### Debug Mode

When enabled (`--debug` flag or `debug_mode=True`):
- Browser runs in non-headless mode (visible)
- Screenshots and HTML saved to `debug_output/{bank_id}/` with timestamps
- Automatic debug capture on errors via `_save_debug_info()`

### Error Handling

Custom exception hierarchy:
- `FintselfException` - Base exception
- `LoginError` - Authentication failures
- `DataExtractionError` - Scraping/parsing failures  
- `ScraperNotFound` - Invalid bank_id
- `OutputError` - File export issues

## Development Standards

- **Language**: Code and docstrings in English, documentation in Spanish
- **Formatting**: Ruff with Black profile
- **Testing**: pytest with mocked HTML fixtures (no real network calls)
- **Logging**: Loguru for structured logging
- **Dependencies**: Managed with `uv`, production deps vs dev deps separated
- **Contributing Guidelines**: Always follow guidelines in CONTRIBUTING.md for development workflow, coding standards, and pull request process

### Commit Guidelines

The project uses **Conventional Commits** for automated releases. Follow this format:

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**

- `feat`: New feature (triggers minor version bump)
- `fix`: Bug fix (triggers patch version bump)
- `docs`: Documentation changes
- `style`: Code formatting changes
- `refactor`: Code refactoring
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks
- `BREAKING CHANGE`: Breaking change (triggers major version bump)

**Examples:**

```bash
feat(scrapers): add support for Banco Estado Chile
fix(cli): resolve authentication error handling
docs: update README with new installation steps
```

**Important:** Never reference CLAUDE.md in commit messages or include Co-Authored-By Claude tags. Commits are automated releases and should not mention AI assistance.

### Git Workflow (Gitflow)

- `main`: Production code (releases only)
- `develop`: Main development branch
- `feature/<name>`: Feature branches created from `develop`

### Pull Request Guidelines

- **Link to Issues**: Reference related issues with `Closes #123`
- **Clear Title**: Use Conventional Commits format
- **Detailed Description**: Explain what and why
- **Small and Focused**: Avoid large multi-purpose PRs
- **Verify Changes**: Run `make test` and `make format` before submitting

## Adding New Scrapers

1. Create feature branch from `develop`: `git checkout -b feature/scraper-bank-xyz develop`
2. Create scraper file in appropriate country folder (e.g., `scrapers/cl/new_bank.py`)
3. Inherit from `BaseScraper` and implement required methods:
   - `_get_bank_id()`: Return unique bank identifier
   - `_login()`: Handle authentication using `self.user/self.password`
   - `_scrape_movements()`: Extract data and return `List[MovementModel]`
4. Save HTML content for tests in `tests/fixtures/cl/new_bank/` (remove sensitive data)
5. Add to `_SCRAPERS` registry in `scrapers/__init__.py`
6. Create test file in `tests/scrapers/cl/test_new_bank.py`
7. Write tests that mock HTML responses (no network calls)
8. Update description in `list_available_scrapers()` function
9. Run `make format` and `make test`
10. Create Pull Request to `develop`

## Testing Strategy

- Tests use HTML fixtures from `tests/fixtures/` instead of live websites
- Mock Playwright page interactions to load local HTML files
- No real credentials or network requests in tests
- Each scraper has isolated test file in `tests/scrapers/`
- Tests are **mandatory** for every scraper

### Release Process

The project uses **automated releases** with Conventional Commits:

1. Pull Requests merged to `main` trigger automated workflow
2. Commits are analyzed to determine version bump type
3. Version is automatically updated in `pyproject.toml`
4. Git tag is created and pushed
5. Release notes are generated automatically
6. Package is published to PyPI
7. GitHub Release is created

**Version Bumping:**
- `fix`: Patch version (1.0.0 → 1.0.1)
- `feat`: Minor version (1.0.0 → 1.1.0)
- `BREAKING CHANGE`: Major version (1.0.0 → 2.0.0)

### Security and Credentials

1. **Environment Variables**: Use format `{BANK_ID}_USER` and `{BANK_ID}_PASSWORD`
2. **Interactive Prompts**: CLI uses `getpass` for secure password input
3. **Debug Files**: Stored in `debug_output/` (Git-ignored)
4. **Test Fixtures**: Remove all sensitive data from HTML fixtures
5. **Never Commit**: Credentials, `.env` files, or real user data