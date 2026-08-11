# Observability Metrics Reference

> Standard metrics collected for each agent execution.

## Core Metrics

| Metric | Type | Description |
|--------|------|-------------|
| run_id | string | Unique pipeline run identifier |
| agent | string | Agent name (e.g., harness-fsd) |
| phase | string | Pipeline phase (requirements_analysis, data_modeling, generation, testing, review) |
| started_at | ISO-8601 | Execution start timestamp |
| ended_at | ISO-8601 | Execution end timestamp |
| duration_ms | integer | Total execution time in milliseconds |
| status | enum | success, failed, timeout, skipped |

## Quality Metrics

| Metric | Type | Description |
|--------|------|-------------|
| schema_valid | boolean | Whether output passes schema validation |
| schema_violations | string[] | List of schema rule violations |
| retry_count | integer | Number of retries needed |

## Resource Metrics

| Metric | Type | Description |
|--------|------|-------------|
| input_size_bytes | integer | Size of input payload |
| output_size_bytes | integer | Size of output payload |
| token_usage.input | integer | Estimated input tokens consumed |
| token_usage.output | integer | Estimated output tokens consumed |
| model | string | Model used for this execution |

## Aggregated Stats (per agent, per pipeline run)

| Stat | Formula |
|------|---------|
| Success Rate | successful_runs / total_runs × 100 |
| Avg Duration | sum(duration_ms) / total_runs |
| Token Efficiency | output_tokens / input_tokens ratio |
| Schema Compliance | schema_valid_runs / total_runs × 100 |
| Avg Retries | sum(retry_count) / total_runs |

## Alert Thresholds

| Condition | Severity | Action |
|-----------|----------|--------|
| success_rate < 80% | High | Notify orchestrator |
| avg_duration > 300s | Medium | Check for performance issues |
| schema_compliance < 90% | High | Review output schemas |
| token_usage > 10k per agent | Medium | Optimize prompts |
| retry_count > 3 | High | Investigate instability |
