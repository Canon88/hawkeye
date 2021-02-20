'''
Author: Canon
Date: 2021-01-24 13:30:41
LastEditTime: 2021-02-20 14:04:35
LastEditors: Please set LastEditors
Description: In User Settings Edit
FilePath: /Code/Jupyter/Beacon/tools/elastic.py
'''

import json

from pandas import json_normalize
from elasticsearch import Elasticsearch, helpers


class Elastic(Elasticsearch):
    def _search(self, **kwargs):
        return super().search(**kwargs)

    def _scan(self, **kwargs):
        return helpers.scan(**kwargs)

    def to_df(self, scroll=True):
        if scroll:
            # results = [item['_source'] for item in self.results]
            results = []
            for item in self.results:
                item['_source']['_id'] = item['_id']
                results.append(item['_source'])
            dataframe = json_normalize(results)
        else:
            results = [item['_source']
                       for item in self.results['hits']['hits']]
            dataframe = json_normalize(results)
        return dataframe

    def Search(self, index, body, scroll=True, **kwargs):
        if scroll:
            self.results = self._scan(
                client=self, index=index, query=body, size=10000, scroll='90m', request_timeout=120, **kwargs)
        else:
            self.results = self._search(index=index, body=body, **kwargs)
        return self
