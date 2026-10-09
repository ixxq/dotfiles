#!/usr/bin/env python3
"""Replay existing findings through live notification templates; default: preview."""

import argparse
import json
import os
import re
import subprocess

REGION = "ap-northeast-1"
CATEGORIES = {
    "threats": ("脅威", "metadata.product.name", "GuardDuty"),
    "exposures": ("露出", "metadata.product.feature.uid", "security-hub/Exposure"),
    "vulnerabilities": ("脆弱性", "metadata.product.name", "Inspector"),
}
ACTIVE = ["New", "In Progress", "Other", "Unknown"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def field(value, path):
    for part in path.split("."):
        match = re.fullmatch(r"([\w-]+)(?:\[(\d+)\])?", part)
        require(match is not None, "Unsupported path: " + path)
        if not isinstance(value, dict) or match[1] not in value:
            return None
        value = value[match[1]]
        if match[2] is not None:
            require(isinstance(value, list), "Expected array: " + path)
            index = int(match[2])
            if index >= len(value):
                return None
            value = value[index]
    return value


def filters_for(account, key, product, severities):
    def condition(name, value, comparison="EQUALS"):
        return {"FieldName": name, "Filter": {"Value": value, "Comparison": comparison}}

    groups = [
        {"StringFilters": [condition("cloud.account.uid", account), condition(key, product),
                           condition("activity_name", "Close", "NOT_EQUALS")], "Operator": "AND"},
        {"StringFilters": [condition("status", value) for value in ACTIVE], "Operator": "OR"},
    ]
    if severities:
        groups.append({"StringFilters": [condition("severity", value) for value in severities], "Operator": "OR"})
    return {"CompositeFilters": groups, "CompositeOperator": "AND"}


def render(transformer, finding):
    values = {}
    prefix = "$.detail.findings[0]."
    for name, path in transformer["InputPathsMap"].items():
        require(path.startswith(prefix) and re.fullmatch(r"[\w-]+(?:\[\d+\])?(?:\.[\w-]+(?:\[\d+\])?)*", path[len(prefix):]), "Unsupported input path: " + path)
        values[name] = field(finding, path[len(prefix):])
        if values[name] is None:
            values[name] = ""  # EventBridge omits variables for missing paths.
        require(isinstance(values[name], str), "Expected string input: " + name)

    def replace(value):
        if isinstance(value, str):
            return re.sub(r"<([\w-]+)>", lambda match: values[match[1]], value)
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    # Parse first so quotes/backslashes in finding titles remain valid JSON.
    message = replace(json.loads(transformer["InputTemplate"]))
    require(message["version"] == "1.0" and message["source"] == "custom", "Unsupported notification format")
    content = message["content"]
    require(len(content["title"]) <= 250 and len(content["description"]) <= 8000, "Notification too long")
    require(all(len(step) <= 350 for step in content.get("nextSteps", [])), "Notification step too long")
    return message


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--rule-prefix", default="security-notifications")
    parser.add_argument("--all-severities", action="store_true", help="Include Low/Medium etc. for this replay only")
    parser.add_argument("--send", action="store_true", help="Publish; without this flag, only preview counts")
    args = parser.parse_args()

    def aws(*command, region=REGION):
        # Do not retry a publish with an ambiguous outcome and risk duplicates.
        env = dict(os.environ, AWS_PAGER="", AWS_MAX_ATTEMPTS="1")
        result = subprocess.run(["aws", "--profile", args.profile, "--region", region, "--output", "json", *command],
                                text=True, capture_output=True, env=env)
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout)

    account = aws("sts", "get-caller-identity")["Account"]
    channels = aws("chatbot", "describe-slack-channel-configurations", region="us-east-2")["SlackChannelConfigurations"]
    planned = []
    for category, (label, key, product) in CATEGORIES.items():
        name = args.rule_prefix + "-" + category
        rule = aws("events", "describe-rule", "--name", name)
        pattern = json.loads(rule["EventPattern"])
        finding_pattern = pattern["detail"]["findings"]
        severities = finding_pattern["severity"]
        metadata = {"product": {"feature": {"uid": [product]}}} if category == "exposures" else {"product": {"name": [product]}}
        expected = {"source": ["aws.securityhub"], "detail-type": ["Findings Imported V2"], "detail": {"findings": {
            "cloud": {"account": {"uid": [account]}}, "metadata": metadata, "severity": severities,
            "activity_name": [{"anything-but": "Close"}], "status": ACTIVE}}}
        require(pattern == expected and rule["State"] == "ENABLED", "Unsupported/disabled rule: " + name)
        targets = aws("events", "list-targets-by-rule", "--rule", name)["Targets"]
        require(len(targets) == 1, "Expected one SNS target: " + name)
        target = targets[0]
        topic = target["Arn"]
        require(topic.startswith(f"arn:aws:sns:{REGION}:{account}:"), "Unexpected target: " + topic)
        destinations = [channel for channel in channels if topic in channel["SnsTopicArns"]]
        require(destinations and all(c.get("State") == "ENABLED" for c in destinations), "No enabled Slack destination")
        subscriptions = aws("sns", "list-subscriptions-by-topic", "--topic-arn", topic)["Subscriptions"]
        require(len(subscriptions) == 1 and subscriptions[0]["Endpoint"] == "https://global.sns-api.chatbot.amazonaws.com",
                "Unexpected SNS subscriber; inspect topic before sending")
        filters = filters_for(account, key, product, None if args.all_severities else severities)
        findings = aws("securityhub", "get-findings-v2", "--filters", json.dumps(filters))["Findings"]
        seen = set()
        for raw in findings:
            finding = json.loads(raw) if isinstance(raw, str) else raw
            uid = finding["metadata"]["uid"]
            require(uid not in seen, "Duplicate finding: " + uid)
            seen.add(uid)
            require(field(finding, "cloud.account.uid") == account and field(finding, key) == product,
                    "Finding outside requested scope")
            require(finding["activity_name"] != "Close" and finding["status"] in ACTIVE, "Finding already closed")
            require(args.all_severities or finding["severity"] in severities, "Severity mismatch")
            planned.append((topic, uid, render(target["InputTransformer"], finding)))
        print(f"{account} {label}: {len(findings)}件 → " + ", ".join("#" + c["SlackChannelName"] for c in destinations), flush=True)
    if not args.send:
        print(f"合計{len(planned)}件。未送信です。送信する場合は --send を追加してください。")
        return
    for index, (topic, uid, message) in enumerate(planned, 1):
        result = aws("sns", "publish", "--topic-arn", topic, "--message", json.dumps(message, ensure_ascii=False))
        print(f"{index}/{len(planned)} SNS受付済み: {uid} MessageId={result['MessageId']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError) as error:
        raise SystemExit(str(error)) from error
