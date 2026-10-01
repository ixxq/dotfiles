# SidePulse

このMacで使っている設定、SidePulse CLIへの変更、日常操作をまとめる。
設定と変更したPythonファイルをchezmoiで直接管理する。
Gitには標準版のファイルを先に登録し、その次のコミットで今回の変更を載せる。
設定ファイルはMac側の`~/.config/sidepulse/agent-monitor/settings.json`にある。
CLIはMac側で動くPythonプログラムを指す。

記録日: 2026-10-01。対象はmacOS、SidePulse Pro（8 LED）、CLI `1.dev71+g6d55225fe`。
このMacには以下の変更を適用済み。確認や記録のために、復元手順をもう一度実行する必要はない。

## 日常操作

### 再起動 / ON

```sh
sidepulse service start && sidepulse status-bar start
```

バックグラウンド処理とメニューバー側の両方を起動する。
このバージョンの`start`は、起動中なら再起動になる。
設定やカスタム演出を保持し、OFFで外れたメニューバーの自動起動登録も復元する。

### 一時OFF

```sh
sidepulse service stop && sidepulse status-bar stop && sidepulse write off --device /Volumes/SidePulse
```

両方の自動制御を止めてから消灯する。メニューバーのSidePulseも終了する。
Codex・Claude Code・開発サーバーの作業は継続できる。復帰には上のONコマンドを使う。

- `sidepulse write off`だけでは、次の状態更新で再点灯することがある。
- `status-bar stop`はメニューバーのLaunchAgent登録ファイルも削除する。`status-bar start`で再作成される。
- `service stop`はバックグラウンド側の登録ファイルを残すため、Macへの再ログイン・再起動で自動起動する。このOFFはログイン中の一時停止として使う。
- デバイスのマウント名が違う場合は、`/Volumes/SidePulse`を実際のパスに置き換える。

### 状態・ログ・設定画面

```sh
# CLIのバージョン
sidepulse --version

# バックグラウンド処理の稼働状態（メニューバー側とは別）
sidepulse service status

# フックの登録内容
sidepulse agent-monitor doctor

# ログから集計したエージェントの状態
sidepulse agent-monitor status

# 最近の表示切り替え / エラー
tail -n 30 ~/.local/state/sidepulse/agent-monitor/status-bar.out.log
tail -n 30 ~/.local/state/sidepulse/agent-monitor/status-bar.err.log
tail -n 30 ~/.local/state/sidepulse/agent-monitor/service.err.log

# 設定画面を開く
sidepulse settings
```

`agent-monitor status`は過去ログを再集計する。常駐処理が持つ現在の状態と異なる場合がある。
表示を調べるときは`status-bar.out.log`と`latest.json`も確認する。
`settings`は必要に応じてメニューバー側を起動するため、OFF中に使うと自動表示が再開する場合がある。

## デフォルトと変更後

この表のデフォルトは、保存したバージョンのコード・設定から確認したもの。
付属READMEの一般説明とは、特に完了色などが異なる場合がある。

| 状況 | デフォルト | 今の設定・変更 |
| --- | --- | --- |
| 待機 / 動作中のセッションなし | 控えめなシアンの待機パルス | 即時消灯（`immediate-off`） |
| 作業 / ツール実行中 | シアンが流れる（`cyan-roll`） | 同じ |
| 承認・入力待ち / エラー | オレンジが明滅（`amber-pulse`） | 同じ |
| 返答の完了（`Stop`） | シアンの完了表示（`cyan-complete`） | 同じ。セッション終了とは区別する |
| セッション終了（`SessionEnd`） | 完了扱い。Codexの標準登録にはこのフックがなかった | Codexにも登録し、終了セッションを表示対象から外す |
| 終了したセッションの古いイベント | 再読込時に表示が戻ることがあった | 終了記録を保持して再点灯を防ぐ |
| Codexの新規・再開・clear | 起動専用の演出なし | 中央から虹が広がる約0.8秒 + 消える約0.4秒 |
| Codex / Claude Codeのcompact中 | 通常の作業中と同じ | 紫のゆっくりした明滅（`purple-attention`） |

起動の虹はアプリの起動だけでなく、Codexのメインセッションの`SessionStart`で
`source`が`startup`・`resume`・`clear`のときに出る。子エージェントやcompact後の再開では出ない。
短時間に重なった起動は1回の演出にまとめる。起動ログの読み直しでは再生しない。

compact表示は、現在有効なセッションの最新イベントが`PreCompact`の間に出る。
`PostCompact`、通常の作業への遷移、割り込み、終了で戻る。
別のセッションもcompact中なら紫を続ける。
虹も紫も、承認・入力待ちやエラーの表示を優先する。

通常の集約は「エラー → 入力待ち → ツール実行 → 長時間処理 → 作業中 → 完了 → 待機」の順。
最後のイベントによる単純な上書きではない。
セッションを1つ終了しても、ほかに動作中のセッションがあればその状態を表示する。

## 管理するファイル

| ファイル | 用途 |
| --- | --- |
| [chezmoiのSidePulse設定](../chezmoi/dot_config/sidepulse/agent-monitor/private_settings.json) | `~/.config/sidepulse/agent-monitor/settings.json`の現在値 |
| [Codex設定](../chezmoi/dot_codex/private_config.toml) | SidePulseの12イベント、`features.hooks`、このMacで承認済みのSidePulseフック状態 |
| [Claude Code設定](../chezmoi/dot_claude/private_settings.json) | SidePulseの12イベント。元からある通知音のフックも保持 |
| [chezmoiのPythonファイル](../chezmoi/dot_local/share/sidepulse/venv/lib/python3.13/site-packages/sidepulse) | 変更後のPythonコード6ファイル。`chezmoi apply`で実行先へ配置 |
| [defaults/settings.json](defaults/settings.json) | `AgentMonitorSettings().to_dict()`から取り出したデフォルト設定 |
| [upstream.json](upstream.json) | 対象バージョン、上流コミット、管理するPythonファイルの一覧 |
| [LICENSE](LICENSE) | 保存したSidePulseコードのMITライセンス |
| [check.py](check.py) / [tests](tests) | 一時コピーへchezmoiのコードを配置して19件の動作確認 |
| [公式README](https://github.com/inteliwear/sidepulse/blob/6d55225fed20a82521b23d86a4df2c4a15dff295/README.md) | 対象バージョンのCLI全体の参考資料 |

設定JSONとデフォルトの差は、待機時の消灯、接続デバイス、初期設定完了フラグの3点。
そのほかの設定値も、現在の状態を見渡せるように保存している。

CLIの差分は以下のとおり。

- `providers.py` / `install.py`: Codexの`SessionEnd`を登録対象に追加し、終了フックのタイムアウトを3秒にする。
- `collector.py`: 返答完了とセッション終了を分け、古いログや子エージェントで終了状態が復活するのを防ぐ。
- `event_animation.py`: Codexの起動演出とcompact中の演出を選ぶ。
- `service.py` / `status_bar.py`: バックグラウンド側・メニューバー側の両方で演出を使う。

Python環境全体、実行ログ、会話履歴、`latest.json`、接続キー、デバイス上の`LEDS.LED`は保存しない。
LaunchAgentは`sidepulse service start`と`sidepulse status-bar start`で生成する。

標準版のコミットには既存の5ファイルをそのまま保存している。
次のコミットでその5ファイルを変更し、`event_animation.py`を追加した。
変更箇所はGitで確認できるため、別の`.patch`ファイルは使わない。

```sh
git -C ~/.dotfiles log -p -- chezmoi/dot_local/share/sidepulse/venv/lib/python3.13/site-packages/sidepulse
```

## 設定の変更をdotfilesへ取り込む

UIで設定を変えたら、chezmoiのソースへ取り込む。

```sh
chezmoi add ~/.config/sidepulse/agent-monitor/settings.json
chezmoi add ~/.codex/config.toml
chezmoi add ~/.claude/settings.json
git -C ~/.dotfiles diff
```

Codex・Claudeの設定全体を取り込むコマンドなので、SidePulse以外の変更も差分に含まれる。
保存したい変更か確認する。今回の取り込みではSidePulse関連のみを既存設定へ追加した。

現在のフックはこのMacのホームディレクトリとPython 3.13の絶対パスを含む。
別のユーザー名・Pythonバージョンへ復元するときは、後述のフック再登録でパスを生成し直す。
Codexの`trusted_hash`は既存の承認値を保存したもの。コマンドやパスを変えた場合は`/hooks`で内容を確認して許可する。

Pythonコードはchezmoi側の6ファイルを編集し、下の検証を実行してから反映する。
実行先を直接編集した場合は、編集したファイルだけを`chezmoi add`で取り込む。
仮想環境や`site-packages`全体を取り込む必要はない。

## 検証

```sh
~/.local/share/sidepulse/venv/bin/python -B ~/.dotfiles/sidepulse/check.py
```

インストール済みのバージョンと配置先を確認してから、一時コピーへchezmoiの6ファイルを重ね、19件のテストを実行する。
chezmoi側の編集は、実行先へ反映する前に検証できる。
インストール済みコード、設定、フック、実機のLEDは書き換えない。
macOSのSidePulse用Python環境を使用し、追加のテストライブラリは不要。

終了時の消灯はCodexアプリとClaude Codeで実機確認済み。
虹とcompactの紫は、通知経路・LEDプログラムの描画をテスト済みだが、実物の見え方はまだ未確認。

## CLIの更新後・別環境への復元

対象の上流コミットは[6d55225fed20a82521b23d86a4df2c4a15dff295](https://github.com/inteliwear/sidepulse/commit/6d55225fed20a82521b23d86a4df2c4a15dff295)。
`sidepulse update`はCLIを置き換えるため、直接入れた変更も失われる。
このchezmoiソースは上記のCLIとPython 3.13の配置先に対応する。
別バージョンへ更新した後にそのまま`chezmoi apply`すると、管理している6ファイルを古いコードで上書きする。
更新時は新しい標準版との差分を確認し、chezmoi側のコード・配置先・`upstream.json`を合わせて更新する。

新規環境でこの記録と同じバージョンを入れる場合は、インストール元を固定する。
セットアップはフックを登録し、常駐処理を起動する。

```sh
curl -fsSL https://sidepulse.io/setup.sh | SIDEPULSE_INSTALL_SPEC='git+https://github.com/inteliwear/sidepulse.git@6d55225fed20a82521b23d86a4df2c4a15dff295' bash
sidepulse --version
```

まず前述の`check.py`で対象バージョン・配置先と動作を確認する。
このMacではすでに実行先とchezmoi側のPythonファイルが一致しているため、今すぐ反映し直す必要はない。
復元先では、コードと設定の差分を確認する。
Codex・ClaudeにはSidePulse以外の設定も含まれるため、特に既存環境では差分を確認する。

```sh
SP_PACKAGE="$HOME/.local/share/sidepulse/venv/lib/python3.13/site-packages/sidepulse"
chezmoi diff "$SP_PACKAGE" ~/.config/sidepulse/agent-monitor/settings.json ~/.codex/config.toml ~/.claude/settings.json
```

反映するときは自動制御を止め、インストール済みコードをバックアップしてから適用する。
以下は同じターミナルで続けて実行する。コマンドが失敗したら、その先へ進まず出力を確認する。

```sh
sidepulse service stop && sidepulse status-bar stop
cp -a "$SP_PACKAGE" "$SP_PACKAGE.backup.$(date +%Y%m%d-%H%M%S)"
chezmoi apply "$SP_PACKAGE" ~/.config/sidepulse/agent-monitor/settings.json ~/.codex/config.toml ~/.claude/settings.json

# 復元先のホーム・Pythonのパスで登録し直す（追加したSessionEndも対象）
sidepulse agent-monitor install codex
sidepulse agent-monitor install claude
sidepulse agent-monitor doctor
```

Codexで必要な承認が表示されたら、`/hooks`でSidePulseの登録内容を確認して許可する。
その後、ONのコマンドで両方の常駐処理を起動する。

```sh
sidepulse service start && sidepulse status-bar start
```

## トラブルシューティング

### 作業しているのにオレンジが残る

オレンジは承認・入力待ち、またはエラーの表示。別のセッションの待ち状態も優先される。
現在のSidePulseは、承認要求を対応する`PostToolUse`まで保留扱いにする。
そのため、許可後も動き続ける開発サーバーなどで「承認待ち」が残ることがある。
この誤判定の根本修正は、今回の変更には含めていない。

まず再起動の1行を試すと、メモリ内の古い待ち判定がクリアされる。
ただし、保存状態やログからの復元、新しい承認要求でオレンジに戻ることがあり、
再起動は完全な状態初期化や根本修正にはならない。

### エージェントを閉じたのに消えない

ほかのセッションが作業中・入力待ちではないか、`SessionEnd`が届いているかを確認する。
返答の終了を表す`Stop`だけでは、セッションを終了したことにはならない。
今回確認したのは通常の終了操作で、強制終了やクラッシュで終了通知が届かない場合は別途確認が必要。

### 設定を戻す・変更を調べる

現在値とデフォルトは次で比較できる（差分がある場合の終了コード1は正常）。

```sh
git diff --no-index ~/.dotfiles/sidepulse/defaults/settings.json ~/.dotfiles/chezmoi/dot_config/sidepulse/agent-monitor/private_settings.json
```

待機時の光り方だけを標準へ戻すなら、SidePulseの設定画面でIdle / ReadyをIdle Pulseにする。
設定変更後は`chezmoi add`で取り込み、READMEの比較表も合わせて更新する。
