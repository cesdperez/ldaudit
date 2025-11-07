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

        def is_inactive_in_all_environments(item):
            environments = item.get('environments', {})
            if not environments:
                return False

            for env_name, env_data in environments.items():
                last_modified = datetime.datetime.fromtimestamp(
                    env_data.get('lastModified', 0) / 1000.0
                )
                if last_modified >= modified_before:
                    return False

            return True

        items = filter(is_inactive_in_all_environments, items)
        items = filter(lambda item: item.get('environments', {}).get(
            'production', {}).get('on', None) == is_on, items)
        if maintainers:
            items = filter(lambda item: item.get('_maintainer', {}).get(
                'firstName', None) in maintainers, items)
        return list(items)

    def __search_directory(self, directory, flag_keys, extensions=None):
        """
        Search directory recursively for flag keys with exact string matching.
        Returns dict {flag_key: [(file_path, line_number), ...]}
        """
        results = {key: [] for key in flag_keys}
        exclude_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'dist', 'build', 'venv', 'env', '.pytest_cache', 'bin', 'obj'}

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if extensions:
                    ext_list = [e.strip().lstrip('.') for e in extensions.split(',')]
                    if not any(file.endswith(f'.{ext}') for ext in ext_list):
                        continue

                file_path = os.path.join(root, file)

                if os.path.getsize(file_path) > 1024 * 1024:
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            for flag_key in flag_keys:
                                if f'"{flag_key}"' in line or f"'{flag_key}'" in line:
                                    results[flag_key].append((file_path, line_num))
                except (UnicodeDecodeError, PermissionError, OSError):
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            for line_num, line in enumerate(f, 1):
                                for flag_key in flag_keys:
                                    if f'"{flag_key}"' in line or f"'{flag_key}'" in line:
                                        results[flag_key].append((file_path, line_num))
                    except:
                        continue

        return {k: v for k, v in results.items() if v}

    def __format_scan_results(self, flags_with_locations, project="default"):
        """
        Format scan results showing flags with their locations in the codebase.
        """
        output = []
        for flag, locations in flags_with_locations:
            flag_key = f"{flag['key']}"
            flag_url = f"https://app.launchdarkly.com/{project}/production/features/{flag['key']}"
            maintainer = flag.get('_maintainer', {}).get('firstName', 'No maintainer')
            created_date = datetime.datetime.fromtimestamp(flag['creationDate'] / 1000.0).strftime('%Y-%m-%d')

            env_statuses = []
            preferred_order = ['production', 'staging', 'dev']
            environments = flag.get('environments', {})

            ordered_envs = []
            for env in preferred_order:
                if env in environments:
                    ordered_envs.append(env)

            for env in sorted(environments.keys()):
                if env not in preferred_order:
                    ordered_envs.append(env)

            for env_name in ordered_envs:
                env_data = environments[env_name]
                status = "ON" if env_data.get('on') else "OFF"
                modified = datetime.datetime.fromtimestamp(
                    env_data.get('lastModified', 0) / 1000.0
                ).strftime('%Y-%m-%d')
                env_statuses.append(f"{env_name.capitalize()}: {status} ({modified})")

            status_line = ", ".join(env_statuses)

            output.append(f"\n{flag_key}")
            output.append(f"  Status: {status_line}")
            output.append(f"  Maintainer: {maintainer}")
            output.append(f"  Created: {created_date}")
            output.append(f"  URL: {flag_url}")
            output.append(f"  Locations:")

            for file_path, line_num in locations:
                output.append(f"    {file_path}:{line_num}")

        return "\n".join(output)

    def __pretty_print(self, items, project="default"):
        output = []
        for flag in items:
            is_on = "`on`" if flag['environments']['production']['on'] else "`off`"
            flag_key = f"{flag['key']}"
            flag_url = f"https://app.launchdarkly.com/{project}/production/features/{flag['key']}"
            maintainer = f"👤 @{flag.get('_maintainer', {}).get('firstName', 'No maintainer')}"
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

    def scan_repo(self, project="default", directory=".", modified_before_months=3, extensions=None, maintainers=None):
        """
        Find inactive feature flags that exist in a codebase directory.
        Searches recursively for exact string matches of flag keys in files.
        """
        if not os.path.isdir(directory):
            print(f"Error: Directory '{directory}' does not exist or is not accessible.")
            return

        print(f"Scanning directory: {os.path.abspath(directory)}")
        if extensions:
            print(f"File extensions: {extensions}")
        print()

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

        all_inactive_flags = inactive_flags_off + inactive_flags_on
        flag_keys = [flag['key'] for flag in all_inactive_flags]

        print(f"Checking {len(flag_keys)} LaunchDarkly flag(s) inactive in all environments against codebase...")
        search_results = self.__search_directory(directory, flag_keys, extensions)

        flags_found = []
        for flag in all_inactive_flags:
            if flag['key'] in search_results:
                flags_found.append((flag, search_results[flag['key']]))

        if not flags_found:
            print(f"\nNo inactive flags found in the codebase.")
            return

        off_count = sum(1 for f, _ in flags_found if not f['environments']['production']['on'])
        on_count = len(flags_found) - off_count

        print(f"\nFound {len(flags_found)} inactive flag(s) in codebase ({off_count} OFF, {on_count} ON)")
        print(self.__format_scan_results(flags_found, project))


if __name__ == "__main__":
    fire.Fire(LaunchDarklyAudit)
