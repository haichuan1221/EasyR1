from nl2sql import dsl_acc_reward

j1 = {
  "bizDslQueryMap": {
    "IM_MESSAGE": {
      "query": {
        "bool": {
          "must": [
            {
              "term": {
                "imApp": "Whatsapp"
              }
            },
            {
              "term": {
                "messageContentType": 101
              }
            },
            {
              "match": {
                "messageContent": "appointment"
              }
            },
            {
              "range": {
                "sendTime": {
                  "lt": "2025-10-14T00:00:00-07:00"
                }
              }
            }
          ]
        }
      }
    }
  },
  "unableSearch": False,
  "unableSearchMessage": ""
}

j2 = {
    "bizDslQueryMap": {
        "TODO": {
            "query": {
                "bool": {
                    "must": [
                      {
                          "match": {
                              "todoTitle": "email"
                          }
                      },
                        {
                          "term": {
                              "isFinished": 1
                          }
                      },
                        {
                          "range": {
                              "modifyTime": {
                                  "gte": "2027-05-17T00:00:00-05:00"
                              }
                          }
                      }
                    ]
                }
            }
        }
    },
    "unableSearch": False,
    "unableSearchMessage": ""
}

# 计算相似度
similarity = dsl_acc_reward(str(j1), str(j1))
print(f"DSL Similarity: {similarity:.4f}")
