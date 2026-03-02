#!/bin/bash
cat /opt/whovoted/public/cache/district_report_TX-15_Congressional_District.json | python3 -c "import json, sys; d=json.load(sys.stdin); print('Keys:', list(d.keys())); print('Has age_groups:', 'age_groups' in d); print('Has new_age_gender:', 'new_age_gender' in d)"
