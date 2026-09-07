"""Shared configuration and bounded GitHub requests; no background services."""
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent


def load_config():
    with (ROOT / 'config.json').open(encoding='utf-8') as stream:
        cfg = json.load(stream)
    for section in ('anti_bot', 'radar', 'review'):
        if not isinstance(cfg[section]['enabled'], bool):
            raise ValueError(f'{section}.enabled must be a boolean')
    if not isinstance(cfg['anti_bot'].get('review_mode'), bool):
        raise ValueError('anti_bot.review_mode must be a boolean')
    threshold = cfg['review']['trust_threshold']
    if isinstance(threshold, bool) or not isinstance(threshold, int) or not 0 <= threshold <= 100:
        raise ValueError('review.trust_threshold must be an integer 0-100')
    cap = cfg['review']['max_users_to_scan']
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
        raise ValueError('review.max_users_to_scan must be a nonnegative integer')
    for section, keys in {
        'anti_bot': ('max_account_age_days', 'min_following_for_suspicion',
                     'max_followers_for_suspicion', 'following_to_followers_ratio'),
        'radar': ('hibernation_days', 'max_starred_to_analyze',
                  'max_releases_to_track', 'max_discoveries'),
    }.items():
        for key in keys:
            value = cfg[section][key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f'{section}.{key} must be nonnegative')
            if key != 'following_to_followers_ratio' and not isinstance(value, int):
                raise ValueError(f'{section}.{key} must be an integer')
    if cfg["radar"]["max_discoveries"] > 100:
        raise ValueError("radar.max_discoveries must be at most 100")
    return cfg


def github_request(method, url, **kwargs):
    response = requests.request(method, url, timeout=20, **kwargs)
    # A missing release is normal; other errors must fail the workflow.
    if not (method == 'GET' and url.endswith('/releases/latest') and response.status_code == 404):
        response.raise_for_status()
    return response
