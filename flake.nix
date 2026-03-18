{
  description = "GitHub Actions Security Sandboxes - Reproducible Dev Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
      in
      {
        devShells.default = pkgs.mkShell {
          name = "github-actions-sandboxes-shell";

          buildInputs = with pkgs; [
            git
            curl
            jq
            gnugrep
            coreutils
            python3
            go
            docker
            docker-compose
            act
            bash
            gawk
          ];

          shellHook = ''
            echo ""
            echo "🚀 GitHub Actions Sandboxes Environment (Nix)"
            echo "------------------------------------------------"
            echo "✔ Tools available:"
            echo "  - act     : $(act --version 2>/dev/null || echo 'not found')"
            echo "  - docker  : $(docker --version 2>/dev/null || echo 'not found')"
            echo "  - python3 : $(python3 --version 2>/dev/null || echo 'not found')"
            echo "  - go      : $(go version 2>/dev/null || echo 'not found')"
            echo "  - git     : $(git --version 2>/dev/null || echo 'not found')"
            echo ""
            echo "👉 Start exfil server : python exfil_server.py"
            echo "👉 Run a sandbox      : act <trigger> --eventpath events/<event>.json"
            echo ""
            if ! docker info >/dev/null 2>&1; then
              echo "⚠️  Docker daemon is not running!"
              echo "   Please start Docker Desktop first."
            else
              echo "✅ Docker is running"
            fi
            echo ""
          '';
        };
      }
    );
}
