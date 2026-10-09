"""What this workspace holds: batches and files, a page at a time."""
from quizforge.client import make_client

client = make_client()
page = client.messages.batches.list(limit=2)
print(f"first page: {len(page.data)} batches, has_more={page.has_more}")
every = list(client.messages.batches.list(limit=2))   # the SDK gets each page
print(f"every page: {len(every)} batches, newest first")
for b in every:
    print(f"  {b.id} {b.processing_status}, {b.request_counts.succeeded} succeeded")
for f in client.files.list():
    print(f"file: {f.id} {f.filename} {f.size_bytes:,} bytes")
