---
name: handoff
description: 作業を Orca の新しい worktree と新しい Claude セッションに引き継ぐ。「新規ワークツリーで」「別のワークツリーで」「新しい worktree を切って」「別セッションで」「ここじゃなくて」などと頼まれたときに使う。git worktree add で自分が作業を続けるのではなく、Orca のサイドバーに新しいセッションが増える形で渡す。
---

# handoff

「新規ワークツリーで」は、Orca 管理の worktree を作り、新しい Claude セッションに作業を渡すこと。自分のセッションで `git worktree add` して作業を続けることではない。よくある流れは、このセッションで Issue を起票し、その Issue の作業を新しい worktree に振る形。

## 何を渡すか決める

- 引数に Issue や PR の番号、URL があれば、それを渡す。
- 引数がなければ、この会話で直前に起票したか話していた Issue を渡す。どれを指すか一つに決まらないときや、Issue がないときは、何を渡すかを短く尋ねる。

## 手順

1. orca-cli スキルで CLI を解決し、ガイドを読む（`orca skills get orca-cli`）。
2. 渡す指示を書く。次を入れる。
   - Issue の番号と URL。まず Issue を読んでから始めるよう書く
   - この会話で決まったこと、調べて分かったこと、済んだ作業（未コミットの変更があればファイルと内容）
   - 残りの作業を順番に（Issue に書いてあれば、そちらを見るよう書けばよい）
   - その作業で守る約束事（コミットメッセージ、PR の作り方、push とマージの扱い、レビューへの返信の仕方など。メモリや CLAUDE.md にあるものを書き写す）
3. 起動する。
   - 新しく作る:
     ```text
     orca worktree create --repo path:<リポジトリのパス> --name <issue-番号-短い説明> --reference <Issue の URL> --no-parent --agent claude --prompt "<指示>" --json
     ```
     - Issue も PR も完全な URL を `--reference` で渡す。`--issue` / `--pr` は番号しか記録されず、タイトルやリポジトリが紐づかない。`--reference` とも併用できない。
     - 作成元は省いてリポジトリの既定（Orca の設定。例: origin/dev）に任せる。依頼者が作業中のブランチから積み上げるよう頼んだときだけ `--base-branch` を付ける。
     - ブランチ名は Orca の既定に任せる。依頼者が名前を指定したときだけ `--branch` を付ける。
   - すでに作った worktree に渡す:
     ```text
     orca agent launch --agent claude --worktree id:<repoId>::<path> --prompt "<指示>" --json
     ```
     id は `orca worktree list --json` で調べる。
4. 結果の `launch.prompt.outcome` が `journaled` か `handed-to-terminal` なら渡せている。worktree の id と `launch.outcome.handle` を依頼者に伝えて終える。

## やらないこと

- 引き継いだ作業を自分で続けない。相手の完了も待たない。
- 応答を受け取れなかったときに、新しく起動し直さない。返ってきた `operationId` を付けて `--retry-launch` で同じコマンドを再実行する。
