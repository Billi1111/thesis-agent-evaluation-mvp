import argparse
from pathlib import Path
from benchmark.generate import build_cases
from environment.backend import Backend

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--ticket',default='TICKET_031'); p.add_argument('--output',default='environment/sample.sqlite')
    a=p.parse_args(); path=Path(a.output)
    if path.exists(): raise SystemExit('Refusing to overwrite existing database; choose a new path.')
    case=next(c for c in build_cases() if c['test_id']==a.ticket)
    backend=Backend(case['initial_state'],path); backend.close(); print(path.resolve())
