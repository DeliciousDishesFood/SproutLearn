# grading（M2A 判分内核）

本包实现 M2A 判分原语：

- `objective.py`：单选 / 判断 / 多选确定性判分；多选全对得分。
- `blank.py`：填空题 strict / smart / ai 三档；ai 使用 Jev `noul`（阈值 0.85），不可用时按配置走通用池或确定性降级并标记 `degraded`。
- `confidence.py`：`0.6*jev_conf + 0.3*coverage + 0.1*(1-anomaly)`，阈值 0.6。
- `grader.py`：题型分发与统一输出。
- `result_service.py`：判分结果写入 `grading_result`，`detail_json` 落库前剔除敏感键。

Jev 业务调用点只允许出现在本包（`blank.py`）；`backend/scripts/probe_llm.py` 是诊断探针，不属于业务调用。
