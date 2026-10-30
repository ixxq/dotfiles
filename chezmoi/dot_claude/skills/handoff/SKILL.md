---
name: handoff
description: 作業を Orca の新しい worktree と新しい Claude セッションに引き継ぐ。「新規ワークツリーで」「別のワークツリーで」「新しい worktree を切って」「別セッションで」「ここじゃなくて」などと頼まれたときに使う。git worktree add で自分が作業を続けるのではなく、Orca のサイドバーに新しいセッションが増える形で渡す。
---

# handoff

「新規ワークツリーで」は、Orca 管理の worktree を作り、新しい Claude セッションに作業を渡すこと。自分のセッションで `git worktree add` して作業を続けることではない。

## 手順

1. orca-cli スキルで CLI を解決し、ガイドを読む（`orca skills get orca-cli`）。
2. 渡す指示を書く。次を入れる。
   - Issue や PR の番号と URL、作業の目的
   - すでに決まったこと、調べて分かったこと、済んだ作業（未コミットの変更があればファイルと内容）
   - 残りの作業を順番に
   - その作業で守る約束事（コミットメッセージ、PR の作り方、push とマージの扱い、レビューへの返信の仕方など。メモリや CLAUDE.md にあるものを書き写す）
3. 起動する。
   - 新しく作る: `orca worktree create --name <短い名前> --no-parent --agent claude --prompt "<指示>" --json`（ベースはリポジトリの既定。作業中のブランチから積み上げるよう頼まれたときだけ `--base-branch` を付ける）
   - すでに作った worktree に渡す: `orca agent launch --agent claude --worktree id:<repoId>::<path> --prompt "<指示>" --json`（id は `orca worktree list --json` で調べる）
4. 結果の `launch.prompt.outcome` が `journaled` か `handed-to-terminal` なら渡せている。worktree の id と、`launch.outcome.handle` を依頼者に伝えて終える。

## やらないこと

- 引き継いだ作業を自分で続けない。相手の完了も待たない。
- 応答を受け取れなかったときに、新しく起動し直さない。返ってきた `operationId` を付けて `--retry-launch` で同じコマンドを再実行する。
