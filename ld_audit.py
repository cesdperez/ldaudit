import requests
from dotenv import load_dotenv
import os
import fire
import datetime
from slack_template import slack_message

load_dotenv()


class LaunchDarklyAudit:

    def __init__(self):
        self.api_key = os.getenv("LD_API_KEY")

    def __fetch_all_live_flags(self, project):
        url = f"https://app.launchdarkly.com/api/v2/flags/{project}"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to fetch flags. HTTP status code: {response.status_code}")

    def __filter(self, items, modified_before, is_archived, is_temporary, is_on, maintainers=None):
        items = filter(lambda item: item['archived'] == is_archived, items)
        items = filter(lambda item: item['temporary'] == is_temporary, items)
        items = filter(lambda item: datetime.datetime.fromtimestamp(
            item.get('environments', {}).get('production', {}).get('lastModified', 0) / 1000.0) < modified_before, items)
        items = filter(lambda item: item.get('environments', {}).get(
            'production', {}).get('on', None) == is_on, items)
        if maintainers:
            items = filter(lambda item: item.get('_maintainer', {}).get(
                'firstName', None) in maintainers, items)
        return list(items)

    def __pretty_print(self, items, project="default"):
        output = []
        for flag in items:
            is_on = "`on`" if flag['environments']['production']['on'] else "`off`"
            flag_key = f"{flag['key']}"
            flag_url = f"https://app.launchdarkly.com/{project}/production/features/{flag['key']}"
            maintainer = f"👤 @{flag['_maintainer']['firstName']}"
            created_date = f"Created: {datetime.datetime.fromtimestamp(flag['creationDate'] / 1000.0).strftime('%Y-%m-%d')}"
            last_modified = f"Modified (production): {datetime.datetime.fromtimestamp(flag['environments']['production']['lastModified'] / 1000.0).strftime('%Y-%m-%d')}"

            output.append(
                f"˃ {is_on} [{flag_key}]({flag_url}) · {maintainer} · {created_date} · {last_modified}")

        return "\n".join(output)

    def list_all(self, project="default"):
        """
        Lists all active feature flags for a given project.
        """
        flags = self.__fetch_all_live_flags(project)
        print(self.__pretty_print(flags['items']))

    def list_inactive(self, project="default", modified_before_months=3, maintainers=None):
        """
        Outputs all inactive feature flags for a given project. The criteria for an inactive flag is that it hasn't been modified in production for the last X months.
        It outputs a message to be pasted on Slack, with links and actionable advice.
        """
        flags = self.__fetch_all_live_flags(project)
        inactive_flags_off = self.__filter(
            items=flags['items'],
            modified_before=datetime.datetime.now(
            ) - datetime.timedelta(days=modified_before_months*30),
            is_archived=False,
            is_temporary=True,
            is_on=False,
            maintainers=maintainers,
        )

        inactive_flags_on = self.__filter(
            items=flags['items'],
            modified_before=datetime.datetime.now(
            ) - datetime.timedelta(days=modified_before_months*30),
            is_archived=False,
            is_temporary=True,
            is_on=True,
            maintainers=maintainers,
        )

        total_inactive_flags = len(inactive_flags_off) + len(inactive_flags_on)

        print(slack_message.format(
            modified_before_months=modified_before_months,
            total_inactive_flags=total_inactive_flags,
            inactive_flags_off=self.__pretty_print(inactive_flags_off),
            inactive_flags_on=self.__pretty_print(inactive_flags_on)
        ))


if __name__ == "__main__":
    fire.Fire(LaunchDarklyAudit)
