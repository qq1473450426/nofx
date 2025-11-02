package agents

import "strings"

// extractJSON 从响应中提取JSON（处理markdown代码块等情况）
// 这是所有Agent共享的工具函数
func extractJSON(response string) string {
	// 去除markdown代码块标记
	response = strings.ReplaceAll(response, "```json", "")
	response = strings.ReplaceAll(response, "```", "")
	response = strings.TrimSpace(response)

	// 查找JSON起始和结束
	start := strings.Index(response, "{")
	if start == -1 {
		return ""
	}

	// 找到匹配的右括号
	depth := 0
	for i := start; i < len(response); i++ {
		if response[i] == '{' {
			depth++
		} else if response[i] == '}' {
			depth--
			if depth == 0 {
				return response[start : i+1]
			}
		}
	}

	return ""
}
