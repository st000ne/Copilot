# Simple policy defaults for the agent runner

# Default maximum reasoning / tool steps per invocation.
# You suggested 10-20; I chose 15 as a sane default.
DEFAULT_MAX_STEPS = 15

# Number of times to retry a failed tool call before giving up on that action.
DEFAULT_MAX_RETRIES = 2

# Per-tool-call timeout in seconds (agent will treat a timeout as a failed Observation).
DEFAULT_TOOL_TIMEOUT_SEC = 30

# When parsing agent outputs, allow some leniency but enforce these prefixes.
THOUGHT_PREFIX = "Thought:"
ACTION_PREFIX = "Action:"
OBSERVATION_PREFIX = "Observation:"
FINAL_ANSWER_PREFIX = "FinalAnswer:"

# Maximum characters of 'thoughts' saved per step (prevent runaway scratchpads).
MAX_THOUGHT_CHARS = 2000
