# Contributing to loop-claudecode

> **loop-claudecode** is a goal-driven, fully autonomous development closed-loop meta-skill for Claude Code. Set a goal, and let the system handle requirements, design, implementation, testing, and repair — automatically looping until convergence.

Thank you for your interest in contributing! 🎉

## Project Status

loop-claudecode is currently **maintained by an individual developer** ([PerryLink](https://github.com/PerryLink)). While I welcome community contributions, please understand that review and merge may take some time. For major changes, please **open an Issue first** to discuss what you would like to change.

## How to Report a Bug

Please use the GitHub Issues tracker. A good bug report includes:

```
**Title**: [Bug] Brief description

**Environment**:
- OS: [e.g. Windows 11, macOS 14, Ubuntu 24.04]
- Claude Code version: [e.g. 2.1.139]
- loop-claudecode version/commit: [e.g. main@abc1234]

**Steps to Reproduce**:
1. Run `/goal "loop-claudecode: ..."`
2. Observe error at phase [part_X_Y]

**Expected Behavior**: [What should happen]
**Actual Behavior**: [What actually happens, include error logs]
**state.json snapshot** (if relevant): [Attach or paste sanitized state.json]
```

## Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/PerryLink/loop-claudecode.git
cd loop-claudecode

# 2. Run the installer (creates symlinks in ~/.claude/skills/)
bash install.sh

# 3. Run validation tests
# Note: validator.py checks termination.status which template files only have as `_ref`.
# For template validation, use --check-template mode if implemented, or skip:
python tools/validator.py state.json.template   # may report schema warnings for template-only fields
python tools/test_runner.py --verbose

# 4. (Optional) Install dev dependencies for linting
pip install pytest jsonschema
```

## Code Standards

- **Python**: Follow [PEP 8](https://peps.python.org/pep-0008/). Use 4-space indentation. Include docstrings for all public functions.
- **Bash**: Follow [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html). Use `set -euo pipefail`. Include header comments explaining each script's purpose.
- **Markdown (SKILL.md)**: Keep phase dispatch tables aligned. Use consistent emoji markers (★ for critical steps, ⚠️ for warnings).

Run before submitting a PR:
```bash
python tools/test_runner.py        # All 6 Golden Tests (T1-T6) must pass
# Note: validator.py on template files may report schema warnings (template uses `_ref` placeholders).
# Use --check-template mode if implemented, or validate against a runtime state.json for full checking.
python tools/validator.py state.json.template  # Schema validation must pass
```

## Pull Request Process

1. **Fork** the repository and create your branch from `main`.
2. **Write or update tests** for any new functionality.
3. **Ensure all tests pass**: `python tools/test_runner.py`
4. **Update documentation** if you change behavior (SKILL.md sections, README).
5. Commit your changes with a descriptive message following [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   git add .
   git commit -m "feat: add X support"  # or fix:, docs:, refactor:, test:, chore:
   ```
6. Push your branch to your fork:
   ```
   git push origin feature/your-feature-name
   ```
7. Open a Pull Request from your branch to `PerryLink/loop-claudecode:main`.
8. **Wait for review**. I may request changes. Be patient — this is a solo-maintained project.

### PR Title Convention

```
[type] Brief description

Types: [Feature] [Fix] [Docs] [Refactor] [Test] [Chore]
Example: [Fix] Correct routing P1 design-vs-impl decision tree
```

## Where to Start

Good first issues are tagged with [`good first issue`](https://github.com/PerryLink/loop-claudecode/labels/good%20first%20issue). Areas that particularly need help:

- **Testing**: Adding more Golden Test scenarios for edge cases
- **Documentation**: Improving phase descriptions in SKILL.md
- **Hook Scripts**: Improving G1/G2/G3 hook coverage and edge-case handling
- **Cross-platform**: Testing on Linux/macOS (developed primarily on Windows)

## License

This project is licensed under **Apache License 2.0**. All contributions are accepted under the same license. See [LICENSE](LICENSE) for details.

## Questions?

Open a [Discussion](https://github.com/PerryLink/loop-claudecode/discussions) or email novelnexusai@outlook.com.

---

**If you find this project helpful, please give it a ⭐️ Star!** It helps others discover loop-claudecode and motivates continued development.
