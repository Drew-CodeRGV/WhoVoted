import json, os, glob

# Check processing jobs
jobs_file = '/opt/whovoted/data/processing_jobs.json'
if os.path.exists(jobs_file):
    with open(jobs_file) as f:
        jobs = json.load(f)
    brooks_jobs = {k: v for k, v in jobs.items() if 'Brooks' in str(v.get('county', '')) or 'Voting_History' in str(v.get('original_filename', ''))}
    print(f"Total jobs: {len(jobs)}")
    print(f"Brooks-related jobs: {len(brooks_jobs)}")
    for jid, j in brooks_jobs.items():
        print(f"\n  Job: {jid[:8]}...")
        print(f"    File: {j.get('original_filename', '?')}")
        print(f"    County: {j.get('county', '?')}")
        print(f"    Status: {j.get('status', '?')}")
        print(f"    Total: {j.get('total_records', 0)}, Processed: {j.get('processed_records', 0)}")
        print(f"    Geocoded: {j.get('geocoded_count', 0)}, Failed: {j.get('failed_count', 0)}")
else:
    print("No processing_jobs.json found")

# Check uploads dir for Brooks files
uploads = glob.glob('/opt/whovoted/uploads/*Voting_History*')
print(f"\nBrooks upload files: {len(uploads)}")
for u in sorted(uploads):
    print(f"  {os.path.basename(u)} ({os.path.getsize(u)} bytes)")

# Check data dir for Brooks output
data_files = glob.glob('/opt/whovoted/data/*Brooks*') + glob.glob('/opt/whovoted/data/*brooks*')
print(f"\nBrooks data files: {len(data_files)}")
for d in data_files:
    print(f"  {os.path.basename(d)}")

# Check public dir
pub_files = glob.glob('/opt/whovoted/public/data/*Brooks*') + glob.glob('/opt/whovoted/public/data/*brooks*')
print(f"\nBrooks public files: {len(pub_files)}")
for p in pub_files:
    print(f"  {os.path.basename(p)}")
