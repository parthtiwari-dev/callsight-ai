from tenacity import retry, stop_after_attempt, wait_exponential

external_api_retry = retry(
    wait=wait_exponential(multiplier=1, min=2, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
