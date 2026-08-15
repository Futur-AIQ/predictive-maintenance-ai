import uuid

# Generated once per process. Every token issued in this run is stamped with
# this nonce and validated against it. When the server restarts the nonce
# changes, making all previously issued tokens immediately invalid.
SERVER_NONCE: str = str(uuid.uuid4())
