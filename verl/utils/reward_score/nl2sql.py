import json
import re


def dsl_format_reward(predict_str: str) -> float:
    """Reward function that checks if the reasoning process is enclosed within <think> and </think> tags, while the final answer is enclosed within <answer> and </answer> tags."""
    pattern = r"^<think>\n.*?\n</think>\n<answer>\n.*?\n</answer>$"
    format_match = re.fullmatch(pattern, predict_str)
    return 1.0 if format_match else 0.0


def calculate_similarity(dsl1, dsl2):
    def compare(a, b):
        if type(a) != type(b):
            return 0, 1  # 类型不同，计为1个节点，0匹配

        if isinstance(a, dict):
            all_keys = set(a.keys()).union(b.keys())
            total = len(all_keys)
            match = 0
            child_total = 0
            child_match = 0

            for key in all_keys:
                a_has = key in a
                b_has = key in b

                if a_has and b_has:
                    match += 1  # 键存在，匹配+1
                    m, t = compare(a[key], b[key])
                    child_match += m
                    child_total += t
                else:
                    # 处理仅存在于一个字典中的键
                    if a_has:
                        m, t = compare(a[key], None)
                    else:
                        m, t = compare(None, b[key])
                    child_total += t

            total += child_total
            match += child_match
            return (match, total)

        elif isinstance(a, list):
            max_len = max(len(a), len(b))
            total = 0
            match = 0

            for i in range(max_len):
                elem_a = a[i] if i < len(a) else None
                elem_b = b[i] if i < len(b) else None
                m, t = compare(elem_a, elem_b)
                match += m
                total += t

            return (match, total)

        else:
            # 处理基本类型（包括None）
            return (1, 1) if a == b else (0, 1)

    match, total = compare(dsl1, dsl2)
    return match / total if total != 0 else 0.0


def dsl_acc_reward(predict_str: str, ground_truth: str) -> float:
    try:
        dsl1 = json.loads(predict_str.replace(
            "```json", "").replace("```", ""))['bizDslQueryMap']
        dsl2 = json.loads(ground_truth.replace(
            "```json", "").replace("```", ""))['bizDslQueryMap']

        return calculate_similarity(dsl1=dsl1, dsl2=dsl2)
    except Exception as e:
        print("exception:",e)
        return 0.0


def math_compute_score(predict_str: str, ground_truth: str) -> float:
    return 0.9 * dsl_acc_reward(predict_str, ground_truth) + 0.1 * dsl_format_reward(predict_str)
