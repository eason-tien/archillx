import subprocess, sys
subprocess.check_call([sys.executable, 'scripts/smoke_test_v34_docs.py'])
print('OK_V36_DASHBOARD_REFINEMENT_SMOKE')
