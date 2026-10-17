import json
import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv


def load_config(path):
    load_dotenv()
    config=json.loads(Path(path).read_text(encoding='utf-8'))
    for m in config['models']:
        for field in ('base_url','model','api_key'):
            if m.get(field+'_env') and os.getenv(m[field+'_env']):
                m[field]=os.environ[m[field+'_env']]
        for field in ('base_url','model','api_key'):
            if field in m: m[field]=os.path.expandvars(m[field])
        if '$' in m['model'] or '$' in m['base_url']: raise ValueError('Unresolved environment variables; copy .env.example to .env')
        if urlparse(m['base_url']).hostname not in ('localhost','127.0.0.1','::1'):
            raise ValueError('This baseline configuration permits local inference only. Review costs before enabling a remote provider.')
    return config
