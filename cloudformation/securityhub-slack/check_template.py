"""Offline regression checks; does not simulate AWS delivery or publish messages."""

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from cfnlint.decode import decode
from notify_existing import filters_for, render


def main():
    transformer = {
        "InputPathsMap": {"title": "$.detail.findings[0].finding_info.title", "uid": "$.detail.findings[0].metadata.uid"},
        "InputTemplate": json.dumps({"version": "1.0", "source": "custom", "content": {
            "title": "[露出 / Low]", "description": "<title>\nhttps://example.com/?findingDetailId=<uid>", "nextSteps": []}}),
    }
    title = '引用" と \\ と <uid>'
    notification = render(transformer, {"finding_info": {"title": title}, "metadata": {"uid": "a" * 64}})
    assert notification["content"]["description"] == title + "\nhttps://example.com/?findingDetailId=" + "a" * 64
    assert json.loads(json.dumps(notification)) == notification
    assert "<title>" in transformer["InputTemplate"]
    assert len(filters_for("123", "metadata.product.name", "Inspector", ["High", "Critical"])["CompositeFilters"]) == 3
    assert len(filters_for("123", "metadata.product.name", "Inspector", None)["CompositeFilters"]) == 2
    template, errors = decode(str(Path(__file__).with_name("template.yaml")))
    assert not errors, errors
    resources = template["Resources"]
    expected = {
        "ThreatRule": ("脅威", "threats", {"name": ["GuardDuty"]}),
        "ExposureRule": ("露出", "exposure", {"feature": {"uid": ["security-hub/Exposure"]}}),
        "VulnerabilityRule": ("脆弱性", "vulnerabilities", {"name": ["Inspector"]}),
    }
    assert {key for key, item in resources.items() if item["Type"] == "AWS::Events::Rule"} == set(expected)

    rule_names = []
    for key, (label, route, product) in expected.items():
        rule = resources[key]["Properties"]
        rule_names.append(rule["Name"])
        pattern = rule["EventPattern"]
        finding = pattern["detail"]["findings"]
        assert rule["EventBusName"] == "default" and rule["State"] == "ENABLED"
        assert pattern["source"] == ["aws.securityhub"]  # No leftover test sources.
        assert pattern["detail-type"] == ["Findings Imported V2"]
        assert finding["cloud"]["account"]["uid"] == [{"Ref": "AWS::AccountId"}]
        assert finding["metadata"]["product"] == product
        expected_severities = {"Medium", "High", "Critical"} if key == "ThreatRule" else {"High", "Critical"}
        assert set(finding["severity"]) == expected_severities
        assert "/".join(finding["severity"]) in rule["Description"]
        assert finding["activity_name"] == [{"anything-but": "Close"}]
        assert set(finding["status"]) == {"New", "In Progress", "Other", "Unknown"}

        assert len(rule["Targets"]) == 1
        target = rule["Targets"][0]
        assert target["Arn"] == {"Ref": "NotificationTopic"}
        assert target["RoleArn"] == {"Fn::GetAtt": ["EventPublishRole", "Arn"]}
        transformer = target["InputTransformer"]
        text = transformer["InputTemplate"]["Fn::Sub"]
        assert set(re.findall(r"<([a-z]+)>", text)) == set(transformer["InputPathsMap"])
        assert transformer["InputPathsMap"]["uid"] == "$.detail.findings[0].metadata.uid"
        assert transformer["InputPathsMap"]["account"] == "$.detail.findings[0].cloud.account.uid"
        # Parse the template itself: catches the previously encountered unquoted <title>.
        notification = json.loads(text)
        assert notification["version"] == "1.0" and notification["source"] == "custom"
        assert notification["content"]["title"] == f"[{label} / <severity>]"
        title, resource_info, link = notification["content"]["description"].split("\n\n")
        assert title == "<title>"
        assert resource_info == "リソース名: <resourcename>\n種類: <resourcetype>\nID: <resourceuid>"
        for variable, resource_field in [("resourcename", "name"), ("resourcetype", "type"), ("resourceuid", "uid")]:
            assert transformer["InputPathsMap"][variable] == "$.detail.findings[0].resources[0]." + resource_field
        sample = {"finding_info": {"title": "Example"}, "metadata": {"uid": "a" * 64, "product": {"name": "Inspector"}},
                  "cloud": {"account": {"uid": "test-account"}, "region": "ap-northeast-1"},
                  "activity_name": "Update", "status": "New", "severity": "High",
                  "resources": [{"name": "First", "type": "AWS::Lambda::Function", "uid": "first-id"},
                                {"name": "Second", "type": "AWS::IAM::Role", "uid": "second-id"}]}
        live_transformer = {"InputPathsMap": transformer["InputPathsMap"], "InputTemplate": text}
        rendered = render(live_transformer, sample)["content"]["description"]
        assert "リソース名: First\n種類: AWS::Lambda::Function\nID: first-id" in rendered
        assert "second-id" not in rendered
        missing_name = dict(sample, resources=[{"type": "AWS::Lambda::Function", "uid": "fallback-id"}])
        assert "ID: fallback-id" in render(live_transformer, missing_name)["content"]["description"]
        assert "<resourcename>" not in render(live_transformer, missing_name)["content"]["description"]
        assert "<resourceuid>" not in render(live_transformer, dict(sample, resources=[]))["content"]["description"]
        # Check the rendered ID and nested filter, not just the URL placeholder.
        sample_uid = "a" * 64
        parsed = urlsplit(link.replace("${AWS::Region}", "ap-northeast-1").replace("<uid>", sample_uid))
        assert parsed.scheme == "https" and parsed.hostname == "ap-northeast-1.console.aws.amazon.com"
        assert parsed.path == "/securityhub/v2/home"
        assert parse_qs(parsed.query) == {"region": ["ap-northeast-1"]}
        fragment_path, fragment_query = parsed.fragment.split("?", 1)
        assert fragment_path == "/" + route
        query = parse_qs(fragment_query)
        assert query["findingDetailId"] == [sample_uid]
        assert query["detailPanelTabId"] == ["Resources"]
        assert query["groupbyfield"] == ["finding_info.title"]
        assert parse_qs(query["search"][0]) == {"metadata.uid": ["\\operator\\:EQUALS\\:" + sample_uid]}
        assert notification["content"]["nextSteps"][-1] == "指摘ID: <uid>"
        assert len(notification["content"]["title"]) < 250
        assert all(len(line) <= 350 for line in notification["content"]["nextSteps"])

    publisher = resources["EventPublishRole"]["Properties"]
    publish_policy = publisher["Policies"][0]["PolicyDocument"]["Statement"]
    assert publish_policy == [{"Effect": "Allow", "Action": "sns:Publish", "Resource": {"Ref": "NotificationTopic"}}]
    trust = publisher["AssumeRolePolicyDocument"]["Statement"][0]
    assert trust["Principal"] == {"Service": "events.amazonaws.com"}
    assert trust["Condition"]["StringEquals"]["aws:SourceAccount"] == {"Ref": "AWS::AccountId"}
    trusted_rules = trust["Condition"]["ArnEquals"]["aws:SourceArn"]
    assert {arn["Fn::Sub"].rsplit("/", 1)[-1] for arn in trusted_rules} == set(rule_names)
    assert all("${AWS::AccountId}" in arn["Fn::Sub"] for arn in trusted_rules)

    channel = resources["SlackChannel"]["Properties"]
    assert channel["SnsTopicArns"] == [{"Ref": "NotificationTopic"}]
    assert channel["LoggingLevel"] == "ERROR"
    assert channel["GuardrailPolicies"] == [{"Fn::Sub": "arn:${AWS::Partition}:iam::aws:policy/CloudWatchReadOnlyAccess"}]
    assert channel["SlackChannelId"] == {"Ref": "SlackChannelId"}
    assert channel["SlackWorkspaceId"] == {"Ref": "SlackWorkspaceId"}
    for resource in resources.values():
        assert {"Key": "Author", "Value": {"Ref": "Author"}} in resource["Properties"]["Tags"]
    assert "AdministratorAccess" not in json.dumps(template)
    assert not re.search(r"\b\d{12}\b", json.dumps(template)), "Hard-coded account ID"
    print("OK: 3 finding filters, notification templates, scoped publisher, channel guardrail, tags")


if __name__ == "__main__":
    main()
