from prometheus_client import Counter, Histogram, Gauge

# Counter for messages processed by intent type
messages_processed = Counter(
    'text_extractor_messages_processed_total',
    'Total number of messages processed',
    ['intent']
)

# Counter for HITL triggers by validation error type
hitl_triggers = Counter(
    'text_extractor_hitl_triggers_total',
    'Total number of HITL triggers',
    ['error_type']
)

# Histogram for workflow execution duration
workflow_duration = Histogram(
    'text_extractor_workflow_duration_seconds',
    'Workflow execution duration in seconds',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Histogram for database operation latency
db_operation_latency = Histogram(
    'text_extractor_db_operation_duration_seconds',
    'Database operation latency in seconds',
    ['operation'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)

# Gauge for RabbitMQ consumer lag
consumer_lag = Gauge(
    'text_extractor_consumer_lag',
    'Number of messages waiting in queue'
)
