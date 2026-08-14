# Contributing to Q - Test Arsenal

Thank you for your interest in contributing to **Q - Test Arsenal**! This document provides guidelines and instructions for contributing to the project.

---

## 🚀 Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/q-test-arsenal.git
   cd q-test-arsenal
   ```
3. **Set up your development environment** using our 2-command interactive setup wizard:
   ```bash
   python3 setup_wizard.py
   source .venv/bin/activate
   ```

---

## ⚡ Development & Diagnostic Setup

1. **Manual Virtual Environment Setup** (if not using `setup_wizard.py`):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
   ```

2. **Install package in editable mode with development dependencies**:
   ```bash
   pip install -e .
   ```

3. **Run automated environment validation**:
   ```bash
   python validate_setup.py
   ```

---

## 🛠️ Making Contributions

1. **Create a new branch for your feature**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow coding and quality standards**:
   - Use type hints for Python functions
   - Follow PEP 8 style guidelines
   - Write clear, descriptive commit messages
   - Maintain documentation and docstrings in English
   - Keep application test credentials inside `scenarios/env.yaml` (never commit sensitive keys or real passwords)

3. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request** on GitHub.

---

## 🔒 Security & Code Quality Checks

Before submitting a Pull Request, run security and static analysis checks:

1. **Bandit** (Static Security Analysis):
   ```bash
   bandit -r q_test_arsenal
   ```

2. **Environment & Component Diagnostics**:
   ```bash
   python validate_setup.py
   ```

---

## 📖 Documentation & Language Guidelines

- **Primary Language**: English is the official language for all codebase documentation, docstrings, commit messages, issues, and Pull Requests.
- **CLI Localization**: Keep user-facing strings localized using `q_test_arsenal.core.i18n`.
- **Updating Docs**: Update `README.md` whenever adding new features or changing CLI functionality.

---

## 📄 License

By contributing to **Q - Test Arsenal**, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
