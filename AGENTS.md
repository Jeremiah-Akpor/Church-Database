# AGENTS.md

## Project Overview

Django project using Pipenv for dependency management with django-unfold admin and security scanning via safety.

## Build/Lint/Test Commands

### Environment Setup
```bash
# Install dependencies
pipenv install

# Install dev dependencies (when added)
pipenv install --dev

# Activate shell
pipenv shell
```

### Django Commands
```bash
# Run development server
pipenv run python manage.py runserver

# Database migrations
pipenv run python manage.py makemigrations
pipenv run python manage.py migrate

# Create superuser
pipenv run python manage.py createsuperuser

# Collect static files
pipenv run python manage.py collectstatic

# Django shell
pipenv run python manage.py shell
```

### Testing
```bash
# Run all tests
pipenv run python manage.py test

# Run specific test file
pipenv run python manage.py test app_name.tests.test_file

# Run specific test class
pipenv run python manage.py test app_name.tests.test_file.TestClassName

# Run single test method
pipenv run python manage.py test app_name.tests.test_file.TestClassName.test_method_name

# Run with verbosity
pipenv run python manage.py test -v 2

# Run with coverage (if coverage installed)
pipenv run coverage run manage.py test
pipenv run coverage report
pipenv run coverage html
```

### Linting and Formatting (Add to dev-packages as needed)
```bash
# Format with black
pipenv run black .

# Check with black
pipenv run black --check .

# Lint with flake8
pipenv run flake8 .

# Lint with pylint
pipenv run pylint app_name/

# Type checking with mypy
pipenv run mypy .

# Import sorting with isort
pipenv run isort .

# Security check
pipenv run safety check
```

## Code Style Guidelines

### Python Style
- Follow PEP 8
- Use 4 spaces for indentation
- Max line length: 88 characters (Black default) or 100
- Use double quotes for strings
- Add trailing commas in multi-line structures

### Imports
```python
# Standard library
import os
from datetime import datetime

# Third-party
from django.db import models
from django.contrib.auth.models import User

# Local application
from .models import MyModel
from .utils import helper_function
```

### Django Conventions
- Use class-based views (CBVs) for complex logic, function-based views (FBVs) for simple cases
- Model names: singular, PascalCase (e.g., `UserProfile`)
- Field names: snake_case (e.g., `created_at`)
- URL names: lowercase with hyphens (e.g., `user-profile`)
- Template names: lowercase with underscores (e.g., `user_profile.html`)
- App names: lowercase, no underscores if possible

### Type Hints
- Use type hints for function parameters and return values
- Use `from typing import List, Dict, Optional, Union`
- Use `|` operator for unions (Python 3.10+)

### Error Handling
- Use specific exceptions, not bare `except:`
- Log exceptions with `import logging; logger = logging.getLogger(__name__)`
- Use Django's `get_object_or_404()` for object retrieval in views
- Handle form validation errors explicitly

### Docstrings
- Use Google-style docstrings
- Document all public modules, classes, methods, and functions

```python
def my_function(param: str) -> bool:
    """Short description.

    Longer description if needed.

    Args:
        param: Description of parameter.

    Returns:
        Description of return value.
    """
    return True
```

### Model Guidelines
- Always define `__str__` method
- Use `Meta` class for verbose names and ordering
- Add `created_at` and `updated_at` fields for tracking
- Use `related_name` for ForeignKey and ManyToManyField
- Use `on_delete` explicitly for ForeignKey

### Security
- Never commit secrets to version control
- Use environment variables for sensitive settings
- Run `pipenv run safety check` before deploying
- Use Django's built-in security features (CSRF, XSS protection, etc.)

### Testing
- Place tests in `app_name/tests/` directory
- Name test files `test_*.py`
- Use Django's `TestCase` or `pytest-django`
- Test models, views, forms, and utilities separately
- Use `setUp()` or `setUpTestData()` for test fixtures
- Mock external services and APIs

### Git
- Write clear, descriptive commit messages
- Use present tense ("Add feature" not "Added feature")
- Reference issues when applicable

## Project Structure

```
project_name/
├── app_name/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_models.py
│   ├── urls.py
│   └── views.py
├── project_name/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
├── Pipfile
└── Pipfile.lock
```
