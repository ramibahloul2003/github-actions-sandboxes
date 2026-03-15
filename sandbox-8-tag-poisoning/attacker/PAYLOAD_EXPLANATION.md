# Tag Poisoning Attack

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
