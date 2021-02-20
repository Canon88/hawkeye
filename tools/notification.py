'''
Author: your name
Date: 2021-01-26 13:25:26
LastEditTime: 2021-02-20 14:06:08
LastEditors: Please set LastEditors
Description: In User Settings Edit
FilePath: /Code/Jupyter/Beacon/notification.py
'''
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
