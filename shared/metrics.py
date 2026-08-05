from prometheus_client import Histogram, Counter

db_operation_latency = Histogram(
    'db_operation_duration_seconds',
    'Database operation latency',
    ['operation']
)

workflow_duration = Histogram(
    'workflow_duration_seconds',
    'LangGraph workflow duration'
)

messages_processed = Counter(
    'messages_processed_total',
    'Total messages processed',
    ['intent']
)

hitl_triggers = Counter(
    'hitl_triggers_total',
    'Total HITL triggers',
    ['error_type']
)