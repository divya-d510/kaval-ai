"""Financial crime & transaction link analysis.

Flags are transparent heuristics, not ML: a transaction is flagged if it's
high-value or linked to an open Cybercrime/Fraud FIR; an account is flagged
as a possible mule account if it transacts with several distinct suspects'
accounts. Restricted to the Supervisor role — see app/core/rbac.py.
"""

from collections import defaultdict

from app.core.catalyst_datastore import get_datastore

MULE_ACCOUNT_THRESHOLD = 4


def _truthy(val) -> bool:
    return str(val).strip().lower() in ("1", "true", "yes")


def financial_network() -> dict:
    store = get_datastore()
    accounts = store.query("financial_accounts", limit=1000)
    transactions = store.query("financial_transactions", limit=5000)
    suspects = {s["suspect_id"]: s["name"] for s in store.query("suspects", limit=1000)}

    account_owner = {a["account_id"]: a["suspect_id"] for a in accounts}
    counterparties = defaultdict(set)
    for t in transactions:
        from_owner = account_owner.get(t["from_account_id"])
        to_owner = account_owner.get(t["to_account_id"])
        if from_owner and to_owner and from_owner != to_owner:
            counterparties[t["from_account_id"]].add(to_owner)
            counterparties[t["to_account_id"]].add(from_owner)

    mule_accounts = {acc for acc, others in counterparties.items() if len(others) >= MULE_ACCOUNT_THRESHOLD}

    nodes = [
        {
            "id": a["account_id"],
            "suspect_id": a["suspect_id"],
            "name": suspects.get(a["suspect_id"], a["suspect_id"]),
            "bank": a["bank_name"],
            "type": a["account_type"],
            "flagged_mule": a["account_id"] in mule_accounts,
        }
        for a in accounts
    ]

    flagged_ids = {t["transaction_id"] for t in transactions if _truthy(t.get("flagged_suspicious"))}
    edges = [
        {
            "source": t["from_account_id"],
            "target": t["to_account_id"],
            "amount": float(t["amount"]),
            "date": t["txn_date"],
            "flagged": t["transaction_id"] in flagged_ids,
            "flag_reason": t.get("flag_reason") or "",
            "fir_id": t.get("fir_id") or None,
        }
        for t in transactions
    ]
    flagged_transactions = [
        {
            "transaction_id": t["transaction_id"],
            "from": t["from_account_id"],
            "to": t["to_account_id"],
            "amount": float(t["amount"]),
            "date": t["txn_date"],
            "reason": t.get("flag_reason") or "",
            "fir_id": t.get("fir_id") or None,
        }
        for t in transactions
        if t["transaction_id"] in flagged_ids
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "flagged_transactions": flagged_transactions,
        "stats": {
            "num_accounts": len(accounts),
            "num_transactions": len(transactions),
            "num_flagged_transactions": len(flagged_transactions),
            "num_mule_accounts": len(mule_accounts),
            "total_flagged_amount": round(sum(t["amount"] for t in flagged_transactions), 2),
        },
    }
