from prometheus_client import Counter, Histogram, Gauge, Summary, start_http_server

MESSAGES_PROCESSED = Counter(
    'regexbot_messages_processed_total',
    'Total number of messages the bot has processed'
)

SED_COMMANDS = Counter(
    'regexbot_sed_commands_total',
    'Total number of sed substitution commands processed'
)

SED_ERRORS = Counter(
    'regexbot_sed_errors_total',
    'Number of errors encountered during sed processing'
)

SUBSTITUTIONS = Counter(
    'regexbot_substitutions_total',
    'Number of successful substitutions (i.e. messages changed)'
)

SUBSTITUTION_LATENCY = Histogram(
    'regexbot_substitution_latency_seconds',
    'Latency (in seconds) for performing a substitution'
)

UNIQUE_CHATS = Gauge(
    'regexbot_unique_chats',
    'Number of unique Telegram chats observed'
)
