"""Incremental listing discovery; failed windows never advance a durable cursor."""
import sqlite3
import threading
import re

from succession.chain import bytes32_to_listing_id

_LOCK = threading.Lock()


def discover(chain, db_path, record, *, budget=20, span=1000):
    domain = f"{record['chain_id']}:{record['listing_contract'].lower()}"
    start = max(0, int(record.get('deployment_block', 0)))
    head = chain.w3.eth.block_number
    with _LOCK, sqlite3.connect(db_path) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS listing_index (
            domain TEXT, listing_id TEXT, block INTEGER,
            PRIMARY KEY(domain,listing_id))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS listing_cursors (
            domain TEXT PRIMARY KEY, floor INTEGER, ceiling INTEGER)''')
        state = conn.execute('SELECT floor,ceiling FROM listing_cursors WHERE domain=?', (domain,)).fetchone()
        floor, ceiling = state if state else (head + 1, head)
        error = None
        # Replay recent blocks to repair shallow reorganizations, then extend
        # forward and backfill history with the remaining bounded RPC budget.
        windows = [(max(start, min(ceiling, head) - 12), head if head < ceiling else min(head, ceiling))] if state else []
        while len(windows) < budget and ceiling < head:
            upper = min(head, ceiling + span)
            windows.append((ceiling + 1, upper))
            ceiling = upper
        prospective_floor = floor
        while len(windows) < budget and prospective_floor > start:
            lower = max(start, prospective_floor - span)
            windows.append((lower, prospective_floor - 1))
            prospective_floor = lower
        # Actual cursors advance only after each successful fetch and commit.
        floor, ceiling = state if state else (head + 1, head)
        for lower, upper in windows:
            try:
                events = chain.contract.events.Listed().get_logs(from_block=lower, to_block=upper)
            except Exception:
                error = 'Listing discovery could not read a block range; it will retry.'
                break
            conn.execute('DELETE FROM listing_index WHERE domain=? AND block BETWEEN ? AND ?', (domain, lower, upper))
            for event in events:
                listing_id = bytes32_to_listing_id(bytes(event['args']['listingId']))
                if re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', listing_id):
                    conn.execute('INSERT OR REPLACE INTO listing_index VALUES (?,?,?)',
                                 (domain, listing_id, event['blockNumber']))
            if lower <= floor <= upper + 1:
                floor = lower
            if lower <= ceiling + 1:
                ceiling = max(ceiling, upper)
            if head < ceiling:
                conn.execute('DELETE FROM listing_index WHERE domain=? AND block>?', (domain, head))
                ceiling = head
            conn.execute('INSERT OR REPLACE INTO listing_cursors VALUES (?,?,?)', (domain, floor, ceiling))
            conn.commit()
        ids = [row[0] for row in conn.execute('SELECT listing_id FROM listing_index WHERE domain=? ORDER BY block DESC', (domain,))]
    return ids, {'complete': error is None and floor <= start and ceiling >= head,
                 'scanned_from_block': floor, 'indexed_to_block': ceiling,
                 'head_block': head, 'error': error}
