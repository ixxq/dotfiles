# Secure Enclave によるコミット署名

Git のコミット署名鍵を macOS の Secure Enclave で管理する。1Password の SSH agent
(`op-ssh-sign`) からの移行。**署名のみ**が対象で、push/pull の SSH 認証は 1Password のまま。

参考: <https://www.mizdra.net/entry/2026/08/07/101542>

## 仕組み

- `sc_auth` で Secure Enclave 内に CTK identity (秘密鍵 + 自己署名証明書) を作る。
- `/usr/lib/ssh-keychain.dylib` が、その identity を **FIDO セキュリティキー**として
  OpenSSH に見せる。鍵タイプは `sk-ecdsa-sha2-nistp256@openssh.com`。
- `ssh-keygen` に `SSH_SK_PROVIDER` で dylib を教えるだけなので、**常駐エージェントは不要**
  (Secretive のような GUI アプリも login item も要らない)。
- `~/.ssh/id_git_sign` は鍵ハンドルであって秘密鍵ではない。秘密鍵は Secure Enclave から出せない。
  ただし現在の `-t none` は使用時認証を行わないため、同じユーザー権限で動くプロセスは
  ユーザー操作なしで署名を要求できる。Secure Enclave が防ぐのは秘密鍵の持ち出しであり、
  ローカルプロセスによる鍵の使用ではない。

### 前提

- macOS 14 (Sonoma) 以降。動作確認は macOS 26.5.2 / OpenSSH 10.2p1。
- **`ssh-keygen` は常に `/usr/bin/ssh-keygen` (Apple ビルド) を絶対パスで呼ぶこと。**
  `ssh-keychain.dylib` は Apple ビルドの OpenSSH と組み合わせる前提で、nix の `pkgs.openssh`
  では動く保証がない。現状 `ssh-keygen` は PATH 上に `/usr/bin` のものしか無いので bare でも
  同じだが、将来 nix 側で openssh を入れると静かに壊れる。

## 現在の構成

| 項目 | 値 |
|---|---|
| M4Pro の signer | Secure Enclave (`hosts/M4Pro/default.nix` で共有設定を上書き) |
| M4Air の signer | Secure Enclave (`hosts/M4Air/default.nix` で共有設定を上書き) |
| identity label | `git-sign` |
| private key protection | `none` (署名時の Touch ID なし) |
| public key hash (SHA1) | `D93C59C037113F3418EAAB2E4EA5277EB34DCE1B` (現在の M4Pro の値) |
| SSH fingerprint | `SHA256:AsbsNi30tI7r4kUqNSHew9DI86raUYeHeYP3MLCjpck` (現在の M4Pro の値) |
| M4Air public key hash (SHA1) | `F4C41FBD5D6FB60859562D2C5619A06A59A78521` |
| M4Air SSH fingerprint | `SHA256:1ByRGYz/aH3EATzuqXW4ILVyhuDL8VpsPzKIKeGnjmY` |
| M4Air 証明書有効期限 | **2036/10/09** (2026/10/12 に作成し、10年に更新済み) |
| 証明書有効期限 | **2036/08/07** (作成時は 2027/08/10 = 1年。下記手順で10年に更新済み) |
| GitHub signing key | M4Pro: id=1103015 `Secure Enclave (M4Pro, signing)` / M4Air: id=1237600 `Secure Enclave (M4Air, signing)` / 旧鍵: id=805051 `1Password (signing)` |
| allowed signers | `home/git.nix` の `allowedSignerKeys` から生成 |

`~/.ssh/allowed_signers` は Home Manager が Nix store へのシンボリックリンクとして管理する。
鍵を追加・変更するときはこのファイルを直接編集せず、`home/git.nix` を更新して rebuild する。

### Git 側の設定

`ssh-keygen` に `SSH_SK_PROVIDER` を渡すラッパーが要る。Git は `gpg.ssh.program` に
環境変数を渡せないため、`hosts/M4Pro/default.nix` と `hosts/M4Air/default.nix` の
`sshSign` でラッパーを生成している。

`user.signingkey` は 1Password 時代のリテラル公開鍵ではなく、**ハンドルファイルのパス**
(`~/.ssh/id_git_sign`) を指定する。sk 鍵はハンドルが無いと署名できない。

Secure Enclave の鍵は作成した端末にしか存在しないので、各端末で別々に作成する。
共有設定は 1Password を `lib.mkDefault` のまま維持し、M4Pro と M4Air のホスト設定で
それぞれ端末専用の鍵ハンドルと signer を指定している。

### Signing key のローテーション

GitHub の `id=805051` `1Password (signing)` は移行前の旧鍵として残している。
新しい鍵の GitHub 登録と署名検証が完了するまでは削除しない。
GitHub は一度 Verified にしたコミットの検証記録を
repository network 内で永続化するため、登録鍵を後から削除しても、その記録がある過去コミットは
Verified のままになる。ただし削除後に初めて push するコミットや、別の repository network で
初めて検証するコミットには登録鍵が必要になる。

ローカル検証は GitHub と異なり、毎回 `~/.ssh/allowed_signers` を参照する。鍵を作り直したら
`home/git.nix` の `allowedSignerKeys` に新しい公開鍵を**追記**し、過去の署名を検証するために
古い鍵も残す。鍵が全ホストで退役した後は、古い鍵の先頭に
`valid-before="YYYYMMDDHHMMSSZ"` を付けると、切り替え前の署名だけを有効にできる。
`allowedSignerKeys` では
`"valid-before=\"YYYYMMDDHHMMSSZ\" ssh-ed25519 AAAA..."` のように引用符をエスケープする。

参考:

- [GitHub: Persistent commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification#persistent-commit-signature-verification)
- [Git: `gpg.ssh.allowedSignersFile`](https://git-scm.com/docs/git-config#Documentation/git-config.txt-gpgsshallowedSignersFile)

## 新規セットアップ

```bash
# 1. 既存の CTK identity が無いことを確認する
#    ssh-keygen -K は identity を選べず、すべてを書き出す。既存 identity がある状態では
#    同名ファイルの衝突や別 identity のハンドルを配置する危険があるため、ここで中止する。
if ! CTK_IDENTITIES=$(sc_auth list-ctk-identities -t ssh); then
  echo "CTK identity の一覧を取得できない" >&2
  exit 1
fi
printf '%s\n' "$CTK_IDENTITIES"
case $CTK_IDENTITIES in
  "Key Type Public Key Hash"*) ;;
  *)
    echo "CTK identity の一覧が期待した形式ではないため中止する" >&2
    exit 1
    ;;
esac
CTK_IDENTITY_COUNT=$(
  printf '%s\n' "$CTK_IDENTITIES" |
    awk 'NR > 1 && NF { count++ } END { print count + 0 }'
)
if (( CTK_IDENTITY_COUNT != 0 )); then
  echo "既存の CTK identity があるため、新規セットアップを中止する" >&2
  exit 1
fi

# 2. Secure Enclave に鍵を作る
#    -k p-256-ne : ECDSA P-256 / non-exportable (Secure Enclave は P-256 のみ対応)
#    -t none     : 使用時認証なし。同じユーザー権限のプロセスは操作なしで署名できる
#                  使用時認証が必要なら -t bio にして署名ごとに Touch ID を要求する
sc_auth create-ctk-identity -l git-sign -k p-256-ne -t none -N git-sign || exit 1

# 3. 今作成した git-sign の SSH fingerprint を控える
#    「現在の構成」の値を流用せず、直前の出力にある git-sign の値を転記する。
sc_auth list-ctk-identities -t ssh || exit 1
EXPECTED_FINGERPRINT='<git-sign identity の SHA256 fingerprint>'
if [[ $EXPECTED_FINGERPRINT != SHA256:* ]]; then
  echo "EXPECTED_FINGERPRINT はSHA256 fingerprintを指定すること" >&2
  exit 1
fi

# 4. SSH 鍵ハンドルを書き出し、git-sign と一致した場合だけ配置する
#    カレントディレクトリに生成されるので注意。入力を閉じ、上書きプロンプトは失敗させる。
EXPORT_DIR=$(mktemp -d) || exit 1
cd "$EXPORT_DIR" || exit 1
if ! /usr/bin/ssh-keygen -w /usr/lib/ssh-keychain.dylib -K -N "" </dev/null; then
  echo "鍵ハンドルを書き出せない。CTK identity の重複や同名ファイルの衝突を確認すること" >&2
  exit 1
fi
if [[ ! -f id_ecdsa_sk_rk || ! -f id_ecdsa_sk_rk.pub ]]; then
  echo "期待した ECDSA-SK 鍵ハンドルが生成されていない" >&2
  exit 1
fi
EXPORTED_FINGERPRINT=$(
  /usr/bin/ssh-keygen -lf id_ecdsa_sk_rk.pub | awk '{ print $2 }'
)
if [[ $EXPORTED_FINGERPRINT != "$EXPECTED_FINGERPRINT" ]]; then
  printf 'fingerprint mismatch: expected=%s actual=%s\n' \
    "$EXPECTED_FINGERPRINT" "$EXPORTED_FINGERPRINT" >&2
  exit 1
fi
mv id_ecdsa_sk_rk     ~/.ssh/id_git_sign     || exit 1
mv id_ecdsa_sk_rk.pub ~/.ssh/id_git_sign.pub || exit 1

# 5. GitHub に Signing Key として登録する
#    Authentication key の枠に入れても署名検証は有効にならない
gh api -X POST /user/ssh_signing_keys \
  -f title="Secure Enclave ($(scutil --get LocalHostName), signing)" \
  -f key="$(cat ~/.ssh/id_git_sign.pub)"

# 6. dotfiles に記録する値を表示する
cat ~/.ssh/id_git_sign.pub
/usr/bin/ssh-keygen -lf ~/.ssh/id_git_sign.pub
sc_auth list-ctk-identities -t sha1 -e hex
```

公開鍵の出力を `home/git.nix` の `allowedSignerKeys` に追記する。過去コミットの検証に必要なので、
既存の鍵は削除しない。併せて fingerprint、public key hash、GitHub key ID を上の「現在の構成」に
反映する。`home/git.nix` とこの文書を保存した後、Home Manager を適用する。

```bash
# 7. dotfiles を反映する
nix run "$HOME/.dotfiles#switch"
```

`-t none` でも署名には FIDO の user-presence フラグが立つが、provider が操作なしで付けるため、
対話的な user presence の証明にはならない。`allowed_signers` に `no-touch-required` を付ける必要はなく、
付けると OpenSSH が `unknown key option` で落ちる。

作成直後の証明書は**有効期限が1年**しかないので、続けて「証明書の更新」を実行して
10年に伸ばしておくこと。

## 証明書の更新

### 期限の正体

期限切れになるのは **Secure Enclave の鍵そのものではなく、CTK identity をラップする
X.509 証明書**。`sc_auth` に有効期間を指定するオプションは無く、作成から**1年固定**。

SSH はこの証明書を使わない (生の公開鍵しか見ない) ので、**証明書を差し替えても SSH 公開鍵は
変わらない**。よって GitHub 側の再登録は不要。

この identity は既に10年証明書 (2036/08/07) に更新済みなので、当面この作業は不要。
M4Air の identity も10年証明書 (2036/10/09) に更新済み。
新しいマシンで作り直したときは、作成直後に一度この手順を通しておくとよい。

期限切れ後の挙動は未確認。`man ssh-keychain` に

> By default, all **valid** ... identities from all SmartCards and persistent tokens
> currently available in the system are provided.

とあり、期限切れの identity が OpenSSH に提供されなくなる可能性がある。`-t none` にしている
ため Touch ID の失敗としては現れず、**ある日いきなり `git commit` が署名エラーで落ちる**
形になる。`commit.gpgsign = true` なのでコミットが一切できなくなる。

### 手順

```bash
# 1. 更新前の状態を控える (あとで fingerprint 不変を確認するため)
sc_auth list-ctk-identities -t sha1 -e hex
sc_auth list-ctk-identities -t ssh

# 2. CSR を作る
#    -h に渡すのは list-ctk-identities のデフォルト表示 = SHA1 (40桁)。
#    -t sha256 -e hex の値を渡すと "No identity found for hash" で落ちる。
#    直前の出力から CN=git-sign の identity に対応する値をコピーする。
HASH='<git-sign identity の SHA1 40桁>'
if [[ ! $HASH =~ ^[0-9A-Fa-f]{40}$ ]]; then
  echo "HASH は40桁のSHA1を指定すること" >&2
  exit 1
fi
cd "$(mktemp -d)"
sc_auth create-ctk-csr -h "$HASH" -f renew.csr -N git-sign

# 3. 使い捨て CA で 10 年署名する
#    証明書は識別のための入れ物にすぎず、SSH の信頼には一切関与しない。
#    LibreSSL の openssl x509 -req に -subj は無い。CN は手順 2 の -N で入れる。
openssl req -x509 -newkey rsa:2048 -keyout ca.key -out ca.crt \
  -days 3650 -nodes -subj "/CN=git-sign-ca"
openssl x509 -req -in renew.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out renew.crt -days 3650

# 4. 取り込む
sc_auth import-ctk-certificate -f renew.crt

# 5. Valid To が伸び、public key hash / SSH fingerprint が変わっていないことを確認
sc_auth list-ctk-identities
sc_auth list-ctk-identities -t ssh
```

### go/no-go 検証 (必須)

手順 5 の `Valid=YES` は `sc_auth` の見解であって、`ssh-keychain.dylib` が同じ判断をするとは
限らない。**既存のハンドルで実際に署名できることを確認するまで、更新は完了とみなさないこと。**

```bash
export SSH_SK_PROVIDER=/usr/lib/ssh-keychain.dylib
cd "$(mktemp -d)"
printf 'renew check\n' > msg.txt
/usr/bin/ssh-keygen -Y sign -f ~/.ssh/id_git_sign -n git msg.txt
printf '%s %s\n' "$(git config user.email)" "$(cat ~/.ssh/id_git_sign.pub)" > allowed_signers
/usr/bin/ssh-keygen -Y verify -f allowed_signers -I "$(git config user.email)" \
  -n git -s msg.txt.sig < msg.txt
```

`Good "git" signature` が出れば成功。失敗した場合は下の「identity 再作成」に進む。

## フォールバック: identity 再作成

証明書更新が効かない場合は identity ごと作り直す。この場合 **SSH 公開鍵が変わる**ので
GitHub への再登録が必要になる。

```bash
# 1. 先に古い identity を削除する ★重要
#    identity が 2 本あると ssh-keygen -K が両方を同じ id_ecdsa_sk_rk に書こうとして
#    上書きプロンプトで詰まる。KEYCHAIN_CERTIFICATES で絞る方法は -w の Secure Key 経路では
#    効かなかった。
cat ~/.ssh/id_git_sign.pub
sc_auth list-ctk-identities -t sha1 -e hex
OLD_HASH='<削除する git-sign identity の SHA1 40桁>'
if [[ ! $OLD_HASH =~ ^[0-9A-Fa-f]{40}$ ]]; then
  echo "OLD_HASH は40桁のSHA1を指定すること" >&2
  exit 1
fi
printf '削除対象: %s\n' "$OLD_HASH"
sc_auth delete-ctk-identity -h "$OLD_HASH"

# 2. 残存する CTK identity を確認する
#    1件でも残る場合は「新規セットアップ」の preflight で停止する。
#    必要な identity は削除せず、この手順を中止すること。
sc_auth list-ctk-identities -t ssh

# 3. 「新規セットアップ」を最初からやり直す。GitHub への新鍵登録と
#    allowedSignerKeys への追記、Home Manager の反映まで実施する

# 4. 新旧の GitHub signing key を確認する
#    id=805051 は新しい鍵の GitHub 登録と検証が完了するまで削除しない
gh api /user/ssh_signing_keys --jq '.[] | "\(.id)\t\(.title)"'
```

## 動作確認

```bash
# ローカル
git log --show-signature -1

# GitHub 側 (Verified バッジが付くか)
gh api /repos/<owner>/<repo>/commits/<sha> --jq '.commit.verification'
# => {"verified": true, "reason": "valid", ...}
```

`gh` で signing key を操作するには `admin:ssh_signing_key` スコープが要る:

```bash
gh auth refresh -h github.com -s admin:ssh_signing_key
```

## トラブルシューティング

| 症状 | 原因 |
|---|---|
| `No identity found for hash` | `-h` に SHA256 や別端末の値を渡している。対象 identity の SHA1 (40桁) を使う |
| `ssh-keygen -K` が上書きプロンプトで止まる | CTK identity が複数ある。不要なものを削除する |
| `allowed_signers:1: bad options: unknown key option` | `no-touch-required` を書いている。不要 |
| `No principal matched` | 新しい公開鍵が `home/git.nix` の `allowedSignerKeys` に無いか、rebuild が未実施 |
| コミットが署名エラーで落ちる | `~/.ssh/id_git_sign` の消失、`ssh-keychain.dylib` のパス変更、identity の消失を先に疑う。`sc_auth list-ctk-identities` で存在と `Valid` を確認 |
| nix で openssh を入れた直後に壊れた | `ssh-keygen` が nix 側に解決されている。`/usr/bin/ssh-keygen` を絶対パスで呼ぶ |

## 検証済み/未検証の区別

このドキュメントのうち実測で確認したもの:

- 新規セットアップ一式 (鍵作成 → 書き出し → GitHub/`allowed_signers` 登録 → 署名・検証)
- M4Air の鍵作成と10年証明書への更新、Home Manager 適用後の Git コミット署名・検証
  (2026-10-12)。M4Pro の過去コミットも検証成功。GitHub への新鍵登録と公開鍵の一致も確認済み。
  GitHub の Verified 表示は、この鍵で署名したコミットを今後 push した際に確認する。
- 証明書更新の全工程を本番 identity `git-sign` で実行し、以下を確認 (2026-08-10):
  - 有効期限が 2027/08/10 → 2036/08/07 に伸びた
  - public key hash / SSH fingerprint / CN が**すべて不変**
  - **更新後も既存ハンドルで署名でき**、`ssh-keygen -Y verify` と `git log --show-signature` が通る
  - 更新後のコミットを push して GitHub 側も `verified=true` / `reason=valid`
  - → CA 署名の証明書を import しても `ssh-keychain.dylib` は identity を提供し続ける
- ハッシュ形式の罠、`-K` のファイル名衝突、`no-touch-required` が弾かれること

未検証:

- 証明書が期限切れになったときに実際どうなるか (10年更新済みなので当面到達しない)
- `sc_auth` が発行する自己署名証明書以外を入れた状態での、SSH 以外の用途 (smartcard ログイン等)
  への影響。ここでは署名にしか使っていないため未確認
