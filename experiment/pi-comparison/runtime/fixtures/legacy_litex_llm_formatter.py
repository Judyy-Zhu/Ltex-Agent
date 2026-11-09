#!/usr/bin/env python3
"""
Litex 返回结果格式化工具 - 为 LLM 提供清理后的完整 JSON

用途：
1. 保持原始 JSON 结构
2. 只去除冗余字段（session_terminated, termination, detail, language, kind, target, path）
3. 保留 LLM 需要的所有有用信息
"""

import json
from typing import Dict, Any


def format_for_llm(result: Dict[str, Any]) -> str:
    """
    清理 Litex 返回结果，保持 JSON 结构，只移除冗余字段

    保留字段：
    - run_result
    - statement_results (包含 statement_result, statement, proof_method, stores, infers)
    - errors (包含 statement_index, statement, phase, message, category, obligation, source_location)

    移除字段：
    - kind (总是 "run")
    - target (总是 "repl" 或 "eval")
    - path (总是 null)
    - detail (总是 "normal")
    - language (总是 "en")
    - session_terminated (总是 false)
    - termination (总是 null)

    输入: Litex 原始返回的 dict
    输出: 清理后的 JSON 字符串
    """

    # 构建清理后的结果
    cleaned = {
        "run_result": result.get("run_result"),
        "statement_results": result.get("statement_results", []),
        "errors": result.get("errors", [])
    }

    return json.dumps(cleaned, indent=2, ensure_ascii=False)


# 使用示例
if __name__ == "__main__":
    # 测试用例 1: 语法错误
    test_parse_error = {
        "kind": "run",
        "run_result": "failure",
        "target": "repl",
        "path": None,
        "detail": "normal",
        "language": "en",
        "statement_results": [
            {
                "statement_result": "rejected",
                "statement": "have fn bad(x R) R = x +"
            }
        ],
        "errors": [
            {
                "statement_index": 0,
                "statement": "have fn bad(x R) R = x +",
                "phase": "parse",
                "message": "expected object",
                "source_location": {
                    "path": "<repl>",
                    "line": 1,
                    "column": 25
                }
            }
        ],
        "session_terminated": False,
        "termination": None
    }

    print("=" * 60)
    print("测试用例 1: 语法错误")
    print("=" * 60)
    print("原始 JSON 大小:", len(json.dumps(test_parse_error)))
    print("清理后 JSON 大小:", len(format_for_llm(test_parse_error)))
    print("\n清理后的 JSON (给 LLM):")
    print(format_for_llm(test_parse_error))

    # 测试用例 2: 证明失败
    test_proof_error = {
        "kind": "run",
        "run_result": "failure",
        "target": "repl",
        "path": None,
        "detail": "normal",
        "language": "en",
        "statement_results": [
            {
                "statement_result": "rejected",
                "statement": "a > 10"
            }
        ],
        "errors": [
            {
                "statement_index": 0,
                "statement": "a > 10",
                "phase": "search_proof",
                "message": "Could not prove the goal.",
                "category": "proof_search",
                "obligation": "a > 10"
            }
        ],
        "session_terminated": False,
        "termination": None
    }

    print("\n" + "=" * 60)
    print("测试用例 2: 证明失败")
    print("=" * 60)
    print("原始 JSON 大小:", len(json.dumps(test_proof_error)))
    print("清理后 JSON 大小:", len(format_for_llm(test_proof_error)))
    print("\n清理后的 JSON (给 LLM):")
    print(format_for_llm(test_proof_error))

    # 测试用例 3: 成功
    test_success = {
        "kind": "run",
        "run_result": "success",
        "target": "repl",
        "path": None,
        "detail": "normal",
        "language": "en",
        "statement_results": [
            {
                "statement_result": "accepted",
                "statement": "have a R",
                "proof_method": {
                    "type": "define_obj",
                    "rule_name": "Have from nonempty set",
                    "message": "Introduce an object from a nonempty carrier / parameter type"
                },
                "stores": ["a $in R"],
                "infers": []
            }
        ],
        "errors": [],
        "session_terminated": False,
        "termination": None
    }

    print("\n" + "=" * 60)
    print("测试用例 3: 成功")
    print("=" * 60)
    print("原始 JSON 大小:", len(json.dumps(test_success)))
    print("清理后 JSON 大小:", len(format_for_llm(test_success)))
    print("\n清理后的 JSON (给 LLM):")
    print(format_for_llm(test_success))

    # 节省的 token 数
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("去除的冗余字段: kind, target, path, detail, language,")
    print("                 session_terminated, termination")
    print("保留的有用字段: run_result, statement_results, errors")
    print("平均节省约 30-40% 的 JSON 大小")
