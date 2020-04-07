"""
Script to generate test data for parsing ua strings. Most data is from the
ua-parser project (https://github.com/ua-parser/uap-core), but we also
include a few ua's of our own.
"""

import os
import json
from urllib.request import urlopen

import yaml


dir = os.path.dirname(os.path.abspath(__file__))
url = "https://raw.githubusercontent.com/ua-parser/uap-core/master/tests"


def generate_data():

    data = {}  # ua -> {}

    # Read os data from ua-parser project
    with urlopen(url + "/test_os.yaml") as f:
        os_data = yaml.load(f)
    for case in os_data["test_cases"]:
        d = data.setdefault(case["user_agent_string"], {})
        d["os"] = case["family"]

    # Read client data from ua-parser project
    with urlopen(url + "/test_ua.yaml") as f:
        client_data = yaml.load(f)
    for case in client_data["test_cases"]:
        ua = case["user_agent_string"]
        if ua.startswith("User agent:"):  # error in the data
            ua = ua.split(":", 1)[-1].lstrip()
        d = data.setdefault(ua, {})
        d["client"] = case["family"]

    # Read data from ourselves
    for case in more_cases:
        d = data.setdefault(case["ua"], {})
        d["client"] = case["client"]
        d["os"] = case["os"]

    # Turn into a list
    test_cases = []
    for ua, d in data.items():
        d["ua"] = ua
        test_cases.append(d)

    # Write
    with open(os.path.join(dir, "ua_data.json"), "wb") as f:
        f.write(json.dumps(test_cases, indent=2).encode())


more_cases = [
    {
        "ua": "Mozilla/5.0 (Windows  10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
        "client": "Firefox",
        "os": "Windows",
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
        "client": "Firefox",
        "os": "Windows",
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "client": "Chrome",
        "os": "Windows",
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134",
        "client": "Edge",
        "os": "Windows",
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
        "client": "IE",
        "os": "Windows",
    },
]


if __name__ == "__main__":
    generate_data()
