# Security Hub → Slack

PJごとにAWSアカウントとSlackチャンネルを分ける運用向けのCloudFormationテンプレートです。PJ名は不要です。アカウントIDはデプロイ先から自動取得し、以下のCLI手順では東京（`ap-northeast-1`）に固定して配置します。

## 作成されるもの

| リソース | 名前・用途 |
| --- | --- |
| SNSトピック | `security-notifications` |
| Amazon QのSlack設定 | `security-notifications-ap-northeast-1` |
| EventBridgeルール | `security-notifications-threats` / `security-notifications-exposures` / `security-notifications-vulnerabilities` |
| IAMロール2個 | SNSへの送信用、Slackの通知用。物理名はCloudFormationが生成 |

ルールは `default` イベントバスの `Findings Imported V2` を受信します。

- 脅威：GuardDuty、露出：`security-hub/Exposure`、脆弱性：Inspector。
- デプロイ先アカウントの脅威はMedium・High・Critical、露出・脆弱性はHigh・Criticalを通知。
- ステータスが `New` / `In Progress` / `Other` / `Unknown`、かつプロバイダーのアクティビティが `Close` 以外。
- 新規検出と、条件を満たす更新を通知。同じ指摘が更新されれば再通知されます。
- 作成時に過去の指摘を一括送信する処理はありません。
- 見出しは `[脅威 / High]` / `[露出 / High]` / `[脆弱性 / Critical]` など。本文にアカウントID、リージョン、指摘IDを掲載します。
- 本文には先頭リソースの名前・種類・IDを表示します。複数リソースがある場合の関連リソースは詳細画面で確認してください。表示ラベルは「リソース名」です。名前がない場合は空欄になりますが、IDも併記します。
- 本文のリンクは、通知された指摘の詳細（Resourcesタブ）を開きます。脅威・露出・脆弱性ごとの画面で `metadata.uid` に絞り、`findingDetailId` に同じIDを設定します。対象アカウントへのログインが必要です。リンクはExcelで確認済みの形式を使用し、東京のSecurity Hubで開きます。
- Amazon Qのログは `ERROR`。EventBridgeの再試行は24時間・185回、DLQは未設定です。
- `Author` タグは全リソースに付きます。既定値は `suzuki` です。

## 通知レベルの考え方

| 種類 | 通知する重大度 | 判断の理由 |
| --- | --- | --- |
| 脅威（GuardDuty） | Medium / High / Critical | Mediumも通常と異なる不審な活動や侵害の可能性を示すため、早めに確認する |
| 露出（Security Hub） | High / Critical | 公開範囲・認証・権限・脆弱性などを組み合わせた危険な状態のうち、重大なものを優先する |
| 脆弱性（Inspector） | High / Critical | ソフトウェアなどの個別の弱点のうち、重大なものを優先する |

脅威は攻撃成功が確定したという意味ではありません。Lowにはポートスキャンや失敗した侵入の試みなどが含まれるため、Slack通知の対象から外し、定期確認の対象とします。露出はインターネット公開だけを意味せず、脆弱性がなくても検出されます。

重大度を広げても既存の指摘がその場で一括送信されることはありません。以後、条件に一致する新規・更新イベントが通知されます。既存分の送信は後述の `notify_existing.py` を使用します。

- [GuardDutyの重大度の定義](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings-severity.html)
- [Security Hubの露出の説明](https://docs.aws.amazon.com/securityhub/latest/userguide/exposure-findings.html)

## 初回だけ必要な準備

1. デプロイ先アカウント・対象リージョンでSecurity Hubが有効であることを確認します。このテンプレートはGuardDuty、Inspector、Security Hub自体を有効化しません。
2. デプロイ先アカウントの[Amazon Q Developer in chat applications](https://console.aws.amazon.com/chatbot/)で「戸田建設」のSlackワークスペースを認可します。認可済みなら再認可は不要です。
3. 通知先のSlackチャンネルを作成し、Amazon Qアプリを招待します（`/invite @Amazon Q`）。チャンネルURL末尾の `C...` などがチャンネルIDです。

ワークスペース名やURLではなく、IDをパラメーターに渡してください。テンプレートはSlackチャンネル自体の作成・アプリの招待・OAuth認可を行いません。

ワークスペースは「戸田建設」（`toda-ict.slack.com`）で、確認済みID `T012Y4GRQ9H` をテンプレートの既定値にしています。今回のチャンネルは `internal-delivery-security`（ID: `C0C79PURGQP`）です。同じワークスペースならIDは共通なので、他PJでは通知先のチャンネルIDを変えるだけです。

## CLIでデプロイ

このディレクトリで実行します。AWS CLI v2があればデプロイ可能です。CDK、Node.js、Pythonは不要です。

```sh
cd ~/.dotfiles/cloudformation/securityhub-slack
```

以下のプロファイルとSlackチャンネルIDをデプロイ先に置き換えてください。`TARGET_PROFILE` に設定したアカウント内に作成されます。

```sh
TARGET_PROFILE='booklift/admin'
SLACK_CHANNEL_ID='C_REPLACE_ME'

aws sso login --profile "$TARGET_PROFILE"
aws sts get-caller-identity --profile "$TARGET_PROFILE"

aws cloudformation deploy \
  --profile "$TARGET_PROFILE" \
  --region ap-northeast-1 \
  --stack-name security-notifications \
  --template-file template.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    SlackChannelId="$SLACK_CHANNEL_ID" \
    Author=suzuki \
  --tags Author=suzuki \
  --no-fail-on-empty-changeset
```

`get-caller-identity` の `Account` が意図したアカウントであることを確認してから `deploy` を実行します。アカウントIDはテンプレートに書き込みません。

同じアカウント・リージョン・スタック名で再実行すると更新になります。新規作成時の必須パラメーターは `SlackChannelId` だけです。別ワークスペースを使う場合は `--parameter-overrides` に `SlackWorkspaceId=T...` を追加できます。`Author` を変える場合はパラメーターとスタックタグの両方を変更してください。

必要なら `deploy` に `--no-execute-changeset` を追加すると、適用せず変更セットだけ作れます。

## 対象範囲と既存設定

- このテンプレートは各PJアカウントに直接配置する用途です。Auditに配置しても他アカウント分を通知する構成にはなりません。
- ルールが監視するのはデプロイ先リージョンのイベントバスです。Security Hubの集約リージョンではリンク済みリージョン分のイベントも含まれます。東京への配置だけで全リージョンが自動的に対象になるわけではありません。
- 同じアカウント・リージョンには1セットを配置します。固定のリソース名があるため、別スタック名で追加配置する用途には使いません。
- haisou-kanriも2026-10-08に手動設定からこのテンプレートへ移行済みです。kouteiと同じ `security-notifications` スタックで管理します。今後は同じ `deploy` コマンドで更新できます。他アカウントの手動設定を自動で引き継ぐテンプレートではありません。

## 確認と削除

デプロイ後はAmazon Qのチャンネル詳細で「テストメッセージを送信」し、Slackへの到達を確認できます。これはSNS以降の確認で、実際のSecurity Hubイベントからの配信確認とは別です。koutei・haisou-kanriへのデプロイと設定確認は実施済みです。kouteiでは既存指摘のSNS直接送信によるSlack到達も確認済みです。Security HubからEventBridgeを経由する通しテスト、およびhaisou-kanri移行後のSlack到達テストは未実施です。

出力の確認：

```sh
aws cloudformation describe-stacks \
  --profile "$TARGET_PROFILE" --region ap-northeast-1 \
  --stack-name security-notifications --query 'Stacks[0].Outputs'
```

このスタックの通知設定を削除する場合：

```sh
aws cloudformation delete-stack \
  --profile "$TARGET_PROFILE" --region ap-northeast-1 \
  --stack-name security-notifications
aws cloudformation wait stack-delete-complete \
  --profile "$TARGET_PROFILE" --region ap-northeast-1 \
  --stack-name security-notifications
```

Slackチャンネル、Security Hub、既存の手動設定は削除しません。サービス側で生成されたCloudWatch Logs等は、このテンプレートの管理対象外です。

## テンプレート変更時のローカル検証

`uv` がある環境で実行します（検証時だけcfn-lintを使用）。

```sh
uv --system-certs tool run --from cfn-lint cfn-lint -t template.yaml -r ap-northeast-1
uv --system-certs run --with cfn-lint python3 check_template.py
```

構文・CloudFormationの参照と型、およびアカウント制限、解決済み除外、送信権限、通知形式の基本条件を確認します。AWS側の実行や配信を再現するテストではありません。

## 既存の指摘を現在の通知形式で送る

AWS CLIとPython 3を使います。AWSに設定された3ルールの入力テンプレートとSNS送信先を読み取り、未解決の既存指摘を当てはめて送ります。ローカルの `template.yaml` ではなく、デプロイ済みの設定が基準です。

まず件数と現在のSlackチャンネルを確認（送信なし）：

```sh
python3 ~/.dotfiles/cloudformation/securityhub-slack/notify_existing.py --profile koutei/admin
```

送信する場合は同じコマンドに `--send` を追加します。標準では現行ルールの重大度（脅威はMedium／High／Critical、露出・脆弱性はHigh／Critical）に限定します。今回だけ脅威のLowや露出・脆弱性のMedium／Lowなども含めたい場合：

```sh
python3 ~/.dotfiles/cloudformation/securityhub-slack/notify_existing.py --profile koutei/admin --all-severities --send
```

- 別PJでは `--profile` を変更します。そのアカウントの現在のSlack送信先が使われます。
- haisou-kanriも `--profile haisou-kanri/admin` だけで実行できます（CloudFormationへ移行済み）。他の手動設定でルール名が異なる場合だけ `--rule-prefix` を指定します。
- Close済み・対応完了等の指摘は除外します。通常のEventBridgeルールや指摘のステータスは変更しません。
- SNSへ直接送るためEventBridgeの通しテストにはなりません。投稿にテスト用・再通知用の文言は追加しません。
- 実行のたびに対象全件を再送します。途中でエラーになった場合も、表示済みのSNS受付済み分は送信済みです。再実行すると重複します。送信結果が不明なエラーでは、Slackを確認してから判断してください。
- このリポジトリの3ルール形式に対応します。異なるフィルター構造やSNSの追加購読先がある場合は、誤送信を避けるため停止します。

## AWS資料

- [SlackChannelConfigurationと初回認可](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-chatbot-slackchannelconfiguration.html)
- [Security Hub V2のイベントとリージョン集約](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-types.html)
- [カスタム通知の形式](https://docs.aws.amazon.com/chatbot/latest/adminguide/custom-notifs.html)
- [EventBridgeからSNSへの実行権限](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
