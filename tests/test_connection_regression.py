"""Offline RPC regression tests — replay recorded testnet responses via vcrpy.

The cassette under tests/cassettes/ was recorded once against the real,
public Arc testnet RPC (https://arc-testnet.drpc.org — no auth, read-only).
Re-running these tests never touches the network: vcrpy replays the exact
recorded HTTP exchange, so a change in web3.py's request shape or a change
in Arc's JSON-RPC response shape would break replay and fail the test.
"""

import vcr

from arc_devkit.core.connection import get_web3

_CASSETTE_DIR = "tests/cassettes"

_vcr = vcr.VCR(
    cassette_library_dir=_CASSETTE_DIR,
    record_mode="once",
    match_on=["method", "host", "path", "body"],
)


@_vcr.use_cassette("testnet_block_number.yaml")
def test_get_web3_block_number_matches_cassette():
    w3 = get_web3()
    block = w3.eth.block_number
    assert isinstance(block, int)
    assert block > 0


@_vcr.use_cassette("testnet_chain_id.yaml")
def test_get_web3_chain_id_matches_cassette():
    w3 = get_web3()
    assert w3.eth.chain_id == 5042002
