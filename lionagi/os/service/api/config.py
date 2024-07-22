from lion_core.setting import LN_UNDEFINED

DEFAULT_RATE_LIMIT_CONFIG = {
    "interval": 60,
    "interval_requests": 1_000,
    "interval_tokens": 1_000_000,
}

CACHED_CONFIG = {
    "ttl": 300,
    "key": None,
    "namespace": None,
    "key_builder": None,
    "skip_cache_func": lambda x: False,
    "serializer": None,
    "plugins": None,
    "alias": None,
    "noself": False,
}

RETRY_CONFIG = {
    "retries": 3,
    "initial_delay": 0,
    "delay": 2,
    "backoff_factor": 2,
    "default": LN_UNDEFINED,
    "timeout": 180,
    "verbose": True,
    "error_msg": None,
    "error_map": None,
}
