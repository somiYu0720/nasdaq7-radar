#!/usr/bin/env python3
"""SEC evidence analysis placeholder; does not classify dilution."""
import json
from pathlib import Path
p=Path(__file__).with_name('sec_events.json')
d=json.loads(p.read_text(encoding='utf-8'))
print('SEC records:',len(d.get('tickers',{})))
