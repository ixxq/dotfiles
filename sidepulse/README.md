# SidePulse

このMacで使っている設定、SidePulse CLIへの変更、日常操作をまとめる。
設定と変更したPythonファイルをchezmoiで直接管理する。
Gitには標準版のファイルを先に登録し、その次のコミットで今回の変更を載せる。
設定ファイルはMac側の`~/.config/sidepulse/agent-monitor/settings.json`にある。
CLIはMac側で動くPythonプログラムを指す。

更新日: 2026-10-09。対象はmacOS、SidePulse Pro（8 LED）、CLI `1.dev71+g6d55225fe`。

## 日常操作

### 本体の起動演出

[INIT.LED](../chezmoi/.chezmoitemplates/sidepulse/INIT.LED)は、Codexのセッション開始と同じ虹。通常の稼働中と同じ流れ方・速さで、色だけ虹色にして1周（約1.75秒）で消灯する。
Macの設定とは別に、SidePulse本体の`/Volumes/SidePulse/INIT.LED`へ保存する。
本体への電源投入時に再生されるほか、ファイルを書き換えた直後にも確認用に再生される（[公式仕様](https://github.com/inteliwear/sidepulse/blob/main/LEDS_FORMAT.md#initial-state)）。
常駐処理が動いていれば、その後は通常のエージェント状態表示へ切り替わる。

原本と[反映スクリプト](../chezmoi/run_after_sidepulse-init.sh.tmpl)をdotfilesで管理する。
Macでは通常の`chezmoi apply`の最後に本体と原本を比較し、差分があるときだけ書き込む。SidePulseサービスの再起動は不要。
未接続ならスキップし、接続後の次の`chezmoi apply`で反映する。接続だけでは反映されない。
内容が同じなら書き込まず、演出を再生し直さない。読み書きのエラーは失敗として返す。
`--exclude=scripts`や通常ファイルだけの個別適用では、この反映スクリプトは実行されない。
元の紫の演出は[defaults/INIT.LED](defaults/INIT.LED)に保存している。

```sh
chezmoi apply
```

この処理だけを実行する場合は次を使う。

```sh
chezmoi apply --source-path ~/.dotfiles/chezmoi/run_after_sidepulse-init.sh.tmpl
```

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
以前の比較表にあった「待機時に即時消灯」は、現在の「青い待機パルスを10分表示して消灯」へ変更済み。

| 状況 | 標準の動作 | 今の動作・加えた変更 |
| --- | --- | --- |
| 作業 / ツール実行中 | シアンが流れる（`cyan-roll`） | 同じ |
| 通常の応答完了（`Stop`） | シアンの完了点灯（`cyan-complete`）を約20分保持 | 同じ。20分の期限もそのまま。セッション終了とは区別する |
| 応答完了から約20分後 | 待機パルスへ切り替わる | 青い待機パルスへ切り替わり、さらに10分で消灯 |
| 動作中のセッションがない | 控えめな待機パルス。指定色はシアン（実機では緑に見える）。繰り返し続ける | 青いパルスを10分繰り返して消灯 |
| Codexアプリ / CLIを終了 | SidePulseの終了フック登録がなく、直前の表示が残り得る | `SessionEnd`を登録し、終了したセッションの表示を解除 |
| Claude Codeを終了 | `SessionEnd`も「完了」として扱い、約20分表示する | 終了したセッションの表示を解除 |
| 終了後の再起動 / ログ再読込 | 古いイベントや子エージェントの表示が戻る場合がある | 終了記録を保持し、再点灯を防ぐ |
| Codexの新規・再開・clear | 起動専用の演出なし | 通常の稼働中と同じ流れ方の虹を1周（約1.75秒） |
| Codex / Claude Codeのcompact中 | 通常の作業中と同じ | ピンクの光が両端から中央へ集まる約2秒周期の波 |
| Codexの通常版`request_user_input` | 質問中もツール実行扱い | 質問中はオレンジ、回答後は通常表示 |
| 承認・入力待ち / エラー | どちらもオレンジが明滅（`amber-pulse`） | 同じ。自動審査や承認済みコマンドによる誤点滅はまだ残る |

起動の虹はアプリの起動だけでなく、Codexのメインセッションの`SessionStart`で
`source`が`startup`・`resume`・`clear`のときに出る。子エージェントやcompact後の再開では出ない。
短時間に重なった起動は1回の演出にまとめる。起動ログの読み直しでは再生しない。

compact表示は、現在有効なセッションの最新イベントが`PreCompact`の間に出る。
`PostCompact`、通常の作業への遷移、割り込み、終了で戻る。
別のセッションもcompact中ならピンクの波を続ける。
起動・compactの演出より、承認・入力待ちやエラーの表示を優先する。

通常の集約は「エラー → 入力待ち → ツール実行 → 長時間処理 → 作業中 → 完了 → 待機」の順。
最後のイベントによる単純な上書きではない。
セッションを1つ終了しても、ほかに動作中のセッションがあればその状態を表示する。
ほかに有効な状態がなければ、青い待機パルスになる。
普通の返答完了後も、約20分間新しいイベントがなければ待機パルスへ戻る。
待機パルスは中央4つのLEDを使う約4秒周期の明滅。
標準の指定色はシアン（中央2つは`#00E5FF`）だが、このSidePulse Proでは緑に見えるため、中央2つを`#0000FF`、その左右を暗い青の`#000060`に変更した。

`Blue Idle Pulse then Off (10 min)`は、標準と同じ4秒周期を150回繰り返してから消灯する。
SidePulse標準のカスタム演出機能と`repeat 150`を使い、Pythonのタイマーや20分の期限は変更しない。
演出を書き込んだ時点から10分を数える。作業再開では通常表示へ切り替わり、次の待機時に数え直す。
再起動・再接続などで演出を書き直した場合も、10分を数え直す。

通常版`request_user_input`は、`PreToolUse`から対応する`PostToolUse`まで質問待ちとして表示する。
同じセッションの別ツールの開始・終了では質問待ちを解除しない。割り込み・セッション終了でも解除する。
非同期版`request_user_input_async`と、自動審査や承認済みコマンドによる誤点滅は、この対応の対象外。

## 管理するファイル

| ファイル | 用途 |
| --- | --- |
| [chezmoiのSidePulse設定](../chezmoi/dot_config/sidepulse/agent-monitor/private_settings.json) | `~/.config/sidepulse/agent-monitor/settings.json`の現在値 |
| [10分の待機パルス](../chezmoi/dot_config/sidepulse/agent-monitor/animations/idle-pulse-10-min.LED) | 青い待機パルスを150回繰り返して消灯するカスタム演出 |
| [本体のINIT.LED](../chezmoi/.chezmoitemplates/sidepulse/INIT.LED) / [反映スクリプト](../chezmoi/run_after_sidepulse-init.sh.tmpl) | 本体起動時の虹と、`chezmoi apply`で差分だけ反映する処理 |
| [defaults/INIT.LED](defaults/INIT.LED) | この本体に元から入っていた紫の起動演出 |
| [Codex設定](../chezmoi/dot_codex/private_config.toml) | SidePulseの12イベント、`features.hooks`、このMacで承認済みのSidePulseフック状態 |
| [Claude Code設定](../chezmoi/dot_claude/private_settings.json) | SidePulseの12イベント。元からある通知音のフックも保持 |
| [chezmoiのPythonファイル](../chezmoi/dot_local/share/sidepulse/venv/lib/python3.13/site-packages/sidepulse) | 変更後のPythonコード6ファイル。`chezmoi apply`で実行先へ配置 |
| [defaults/settings.json](defaults/settings.json) | `AgentMonitorSettings().to_dict()`から取り出したデフォルト設定 |
| [upstream.json](upstream.json) | 対象バージョン、上流コミット、管理するPythonファイルの一覧 |
| [LICENSE](LICENSE) | 保存したSidePulseコードのMITライセンス |
| [check.py](check.py) / [tests](tests) | 一時コピーへchezmoiのコード・設定・演出を配置して23件の動作確認 |
| [公式README](https://github.com/inteliwear/sidepulse/blob/6d55225fed20a82521b23d86a4df2c4a15dff295/README.md) | 対象バージョンのCLI全体の参考資料 |

設定JSONとデフォルトの差は、待機演出の選択、カスタム演出の登録、接続デバイス、初期設定完了フラグの4点。
そのほかの設定値も、現在の状態を見渡せるように保存している。

CLIの差分は以下のとおり。

- `providers.py` / `install.py`: Codexの`SessionEnd`を登録対象に追加し、終了フックのタイムアウトを3秒にする。
- `collector.py`: 返答完了とセッション終了を分け、古いログや子エージェントで終了状態が復活するのを防ぐ。通常版`request_user_input`の質問待ちを識別する。
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
chezmoi add ~/.config/sidepulse/agent-monitor/animations
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

インストール済みのバージョンと配置先を確認してから、一時コピーへchezmoiの6ファイルと設定・演出を重ね、23件のテストを実行する。起動・compactの演出も、ファームウェアのサイズ制限、描画の変化を確認する。
chezmoi側の編集は、実行先へ反映する前に検証できる。
インストール済みコード、設定、フック、実機のLEDは書き換えない。
macOSのSidePulse用Python環境を使用し、追加のテストライブラリは不要。

本体の起動演出の自動反映は、次の独立したチェックで検証する。

```sh
python3 ~/.dotfiles/sidepulse/check_device_init.py
```

chezmoiのソース・設定・状態DBとディスクを一時ディレクトリへ分離し、未接続、差分反映、同一内容の書き込み省略、本体側の変更の修復、エラー時の内容保持を確認する。実機には書き込まない。

テストは終了通知、質問への回答前後、並行セッション、状態復元、演出の描画・明るさ調整を対象とする。
起動は標準の稼働中と色以外の動きが一致し、compactはピンクの波が両端から中央へ集まることを確認する。本体の`INIT.LED`とセッション開始のプログラムの一致も検証する。
待機パルスは青だけで10分間明滅した後に消灯し、定期更新では再開始せず、作業再開後の待機で再開始することを確認する。

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
このMacのPythonファイルは反映済み。設定・カスタム演出は適用前に差分を確認する。
復元先では、コードと設定の差分を確認する。
Codex・ClaudeにはSidePulse以外の設定も含まれるため、特に既存環境では差分を確認する。

```sh
SP_PACKAGE="$HOME/.local/share/sidepulse/venv/lib/python3.13/site-packages/sidepulse"
chezmoi diff "$SP_PACKAGE" ~/.config/sidepulse/agent-monitor ~/.codex/config.toml ~/.claude/settings.json
```

反映するときは自動制御を止め、インストール済みコードをバックアップしてから適用する。
以下は同じターミナルで続けて実行する。コマンドが失敗したら、その先へ進まず出力を確認する。

```sh
sidepulse service stop && sidepulse status-bar stop
cp -a "$SP_PACKAGE" "$SP_PACKAGE.backup.$(date +%Y%m%d-%H%M%S)"
chezmoi apply "$SP_PACKAGE" ~/.config/sidepulse/agent-monitor ~/.codex/config.toml ~/.claude/settings.json

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

### エージェントを閉じても作業中の表示が残る

ほかのセッションが作業中・入力待ちではないか、`SessionEnd`が届いているかを確認する。
返答の終了を表す`Stop`だけでは、セッションを終了したことにはならない。
今回確認したのは通常の終了操作で、強制終了やクラッシュで終了通知が届かない場合は別途確認が必要。
正常に終了した後も青い待機パルスを10分表示する。その間に新しい作業がなければ消灯する。

### 設定を戻す・変更を調べる

現在値とデフォルトは次で比較できる（差分がある場合の終了コード1は正常）。

```sh
git diff --no-index ~/.dotfiles/sidepulse/defaults/settings.json ~/.dotfiles/chezmoi/dot_config/sidepulse/agent-monitor/private_settings.json
```

待機表示を標準へ戻すなら、SidePulseの設定画面でIdle / ReadyをIdle Pulseにする。待機時に即時消灯するならImmediate Offにする。
設定変更後は`chezmoi add`で取り込み、READMEの比較表も合わせて更新する。
