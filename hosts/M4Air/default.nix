{ username, pkgs, ... }:
let
  # ssh-keychain.dylib は Apple ビルドの OpenSSH と組み合わせて使う。
  sshSign = pkgs.writeShellScript "ssh-sign" ''
    export SSH_SK_PROVIDER=/usr/lib/ssh-keychain.dylib
    exec /usr/bin/ssh-keygen "$@"
  '';
in
{
  # 鍵は端末外に持ち出せないため、M4Air 専用のハンドルを使う。
  # セットアップ手順は docs/secure-enclave-signing.md
  home-manager.users.${username}.programs.git.signing = {
    key = "/Users/${username}/.ssh/id_git_sign";
    signer = "${sshSign}";
  };
}
