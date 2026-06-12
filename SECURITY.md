# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < 1.0   | :x:                |

Only the latest commit on the `main` branch is actively supported with security updates.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub Issues.**

Instead, please report them via email to:

**novelnexusai@outlook.com**

Include the following in your report:

- A clear description of the vulnerability
- Steps to reproduce the issue
- Affected versions/components
- Any potential mitigations you've identified

You should receive a response within **72 hours**. If the issue is confirmed,
we will release a patch as soon as possible depending on complexity,
typically within 7 days.

### What to Expect

| Stage | Timeline |
|-------|----------|
| Initial acknowledgment | Within 72 hours |
| Confirmation of vulnerability | Within 5 business days |
| Patch release | Typically within 7 days of confirmation |
| Public disclosure | After patch is released and users have had time to update |

## Security Considerations for loop-claudecode

### OS-Level Hook Scripts

loop-claudecode includes three OS-level hook scripts (`hooks/`) that run
**outside of Claude Code's AI context** as an out-of-band safety mechanism:

- **G1 (Tamper-Proof Gate):** Protects `gate_state.json` from AI tampering — the
  file is physically isolated from the AI agent's context.
- **G2 (Dangerous-Operation Gate):** Blocks dangerous operations (rm -rf,
  destructive git commands, etc.) unless explicitly allowed.
- **G3 (Completion Declaration Gate):** Stop Hook that enforces Default-FAIL via
  multi-layer verification before allowing termination.

These scripts:
- Are installed with `chmod 555` (read+execute, no write)
- Ship with a `.checksums.sha256` file (read-only, `chmod 444`) for integrity verification
- Should be reviewed before activation: `bash install.sh --with-hooks`

**Note:** Running `hooks/install-gates.sh` independently will NOT set correct
permissions. Always install via `bash install.sh --with-hooks` to ensure hooks
receive `chmod 555` and checksums receive `chmod 444`.

**Always verify hook script checksums before running in production:**
```bash
sha256sum -c ~/.claude/skills/loop-claudecode/hooks/.checksums.sha256
```

### State File Integrity

The `state.json` and `gate_state.json` files control the agent's behavior.
Untrusted modifications to these files could:
- Bypass safety gate checks
- Skip verification phases
- Alter routing decisions

**Recommendations:**
- Keep `.claude/loop-claudecode/` in your project's `.gitignore`
- Do not share `state.json` from completed runs (may contain project internals)
- The `gate_state.json` physical isolation ensures termination state cannot be
  tampered with by the AI agent context

### Dependency Security

loop-claudecode depends on:
- **jq** — for JSON processing in hook scripts. Keep updated via your package manager.
- **Python 3** — for validator and test runner tools. Only stdlib; no pip dependencies required.

Run `bash install.sh --check` to verify your environment before installation.

### Supply Chain

All releases are published through the official GitHub repository:
[https://github.com/PerryLink/loop-claudecode](https://github.com/PerryLink/loop-claudecode)

There are no npm/PyPI/cargo packages. Always clone from the official repo.

## Disclosure Policy

We follow a coordinated disclosure process:

1. Reporter submits vulnerability via email
2. We acknowledge within 72 hours
3. We investigate and develop a fix
4. We release the patch
5. We publish a security advisory on GitHub after users have had reasonable time to update

We appreciate responsible disclosure and will credit reporters in our advisories
(unless you prefer to remain anonymous).
