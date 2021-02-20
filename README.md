<!--
 * @Author: your name
 * @Date: 2020-06-16 15:10:48
 * @LastEditTime: 2021-02-20 14:39:23
 * @LastEditors: Please set LastEditors
 * @Description: In User Settings Edit
 * @FilePath: /Code/Users/canon/Documents/github/hawkeye/README.md
--> 

# HawkEye Beacon
---
主要用于检测数据的周期性请求；
- 支持从ElasticSearch获取数据并进行数据分析；
- 支持ElasticSearch上任意数据的周期性分析；
- 支持Slack告警推送；
- 输出日志中新增`raw_url`以及`beacon_url`链接，便于快速定位异常数据；

```json
{
    "src_ip": "192.168.199.41",
    "dest_ip": "151.101.0.133",
    "dest_port": 443,
    "percent": 85,
    "interval": 600,
    "total": 128,
    "occurrences": 59,
    "raw_url": "https://127.0.0.1:5601/goto/92797ca92e6973ca515468acddc7d99a",
    "beacon_url": "https://127.0.0.1:5601/goto/db3ffb8022b4f83434e006424fdc4d3a",
    "create_time": "2021-02-19T13:42:46.347Z",
    "from_time": "2020-09-22T13:41:55.080Z",
    "to_time": "2021-02-19T13:41:55.080Z",
    "period": 3600,
    "event_type": "beaconing"
}
```