{ pkgs, ... }:
let
  miseVersion = "2026.10.17";
  # Use the official binary until nixpkgs includes the CA trust fix in 2026.10.17.
  miseBin = pkgs.stdenv.mkDerivation {
    pname = "mise-bin";
    version = miseVersion;
    src = pkgs.fetchurl {
      url = "https://github.com/jdx/mise/releases/download/v${miseVersion}/mise-v${miseVersion}-macos-arm64.tar.gz";
      hash = "sha256-18UMFoNSSnZCYJhszJxBwN5eH81JFxS1ZAtle3Z4GvY=";
    };
    dontConfigure = true;
    dontBuild = true;
    installPhase = ''
      runHook preInstall
      install -Dm755 bin/mise $out/bin/mise
      runHook postInstall
    '';
    meta.mainProgram = "mise";
  };
in
{
  programs.mise = {
    enable = true;
    package = miseBin;
    enableZshIntegration = false; # handled via cache_eval + zsh-defer in zsh.nix
  };
}
