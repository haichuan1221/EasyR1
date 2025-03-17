from nl2sql import dsl_acc_reward


j1 = """
{
  "think": "用户想要搜索自己上周发送的所有邮件。需要在 EMAIL 表中查询 isSelfSent 为 true，并且 sendTime 在上周的时间范围内的邮件。",
  "bizDslQueryMap": {
    "EMAIL": {
      "query": {
        "bool": {
          "must": [
            {
              "term": {
                "isSelfSent": true
              }
            },
            {
              "range": {
                "receiveTime": {
                  "gte": "2025-01-06T00:00:00+08:00",
                  "lte": "2025-01-12T23:59:59+08:00"
                }
              }
            }
          ]
        }
      }
    }
  },
  "unableSearch": false,
  "unableSearchMessage": ""
}
"""

j2 = """
{
  "think": "用户想要搜索自己上周发送的所有邮件。需要在 EMAIL 表中查询 isSelfSent 为 true，并且 sendTime 在上周的时间范围内的邮件。",
  "bizDslQueryMap": {
    "EMAIL": {
      "query": {
        "bool": {
          "must": [
            {
              "term": {
                "isSelfSent": true
              }
            },
            {
              "range": {
                "receiveTime": {
                  "gte": "2025-01-07T00:00:00+08:00",
                  "lte": "2025-01-12T23:59:59+08:00"
                }
              }
            }
          ]
        }
      }
    }
  },
  "unableSearch": false,
  "unableSearchMessage": ""
}
"""

# 计算相似度
similarity = dsl_acc_reward(j1, j2)
print(f"DSL Similarity: {similarity:.4f}")
