# src/jobs/orders.py
import time
def place_supplier_order(payload: dict):
    # TODO: map supplier_id -> API creds, format, endpoint
    print("[ORDER] placing", payload)
    time.sleep(1)  # simulate
    # POST to supplier; store PO #; email customer; etc.
    return True
