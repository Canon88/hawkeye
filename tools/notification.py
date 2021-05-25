'''
Author: your name
Date: 2021-01-26 13:25:26
LastEditTime: 2021-05-24 15:50:35
'''

import sys
import json
import uuid
from thehive4py.api import TheHiveApi
from thehive4py.exceptions import AlertException
from thehive4py.models import Alert, AlertArtifact, CustomFieldHelper
from slack_webhook import Slack as SLACK
import pandas as pd


class Slack():
    def __init__(self, webhook):
        self.webhook = webhook

    def _slack(self, text, blocks):
        slack = SLACK(url=self.webhook)
        slack.post(text=text, blocks=blocks)

    def section(self, k, v):
        blocks = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*{}:*   {}".format(k, v)
            }
        }
        return blocks

    def notify(self, text, blocks):
        self._slack(text=text, blocks=blocks)


class TheHive():
    def __init__(self, url, api, version=4):
        self.api = TheHiveApi(url, api, version=version)

    def _build_alert(self, body, **kwargs):
        # Prepare observables
        artifacts = []
        for k, v in body['artifacts'].items():
            for i in v:
                artifacts.append(
                    AlertArtifact(dataType=k, data=i, **kwargs)
                )
        
        # build alert instance
        alert = Alert(
            title=body['title'], tags=body['tags'], type=body['type'],
            tlp=body.get('tlp', 3), description=json.dumps(body['description']),
            source=body['source'],sourceRef=str(uuid.uuid4())[0:6],
            artifacts=artifacts, externalLink=body.get('link')
        )
        return alert

    def notify(self, data):
        # Create the alert
        try:
            alert = self._build_alert(data)
            response = self.api.create_alert(alert)

            # Print the JSON response
            print(json.dumps(response.json(), indent=4, sort_keys=True))

        except AlertException as e:
            print("Alert create error: {}".format(e))