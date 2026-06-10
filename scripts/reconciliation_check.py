#!/usr/bin/env python3
"""
Reconciliation check: Compare account balances vs accounting (transaction-derived).
Run daily via cron job. Outputs discrepancy report.
"""
import subprocess
import json
import sys

def run_psql(sql):
    result = subprocess.run(
        ["docker", "exec", "finance_db", "psql", "-U", "finance_user", "-d", "finance_db", "-t", "-A", "-c", sql],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def main():
    # 1. Get account balances per user
    account_sql = """
    SELECT user_id, SUM(balance) as total
    FROM accounts
    GROUP BY user_id
    ORDER BY user_id;
    """
    account_data = {}
    for line in run_psql(account_sql).split('\n'):
        if line.strip():
            uid, total = line.split('|')
            account_data[int(uid)] = float(total)

    # 2. Get accounting balance per user (income - expenses, adjustments count)
    accounting_sql = """
    SELECT user_id, 
           SUM(CASE WHEN type = 'INCOME' THEN amount 
                    WHEN type = 'EXPENSE' THEN -amount 
                    ELSE 0 END) AS sisa_saldo
    FROM transactions
    WHERE is_deleted = false
    GROUP BY user_id
    ORDER BY user_id;
    """
    accounting_data = {}
    for line in run_psql(accounting_sql).split('\n'):
        if line.strip():
            uid, sisa = line.split('|')
            accounting_data[int(uid)] = float(sisa)

    # 3. Get usernames
    user_sql = "SELECT id, username FROM users ORDER BY id;"
    user_names = {}
    for line in run_psql(user_sql).split('\n'):
        if line.strip():
            uid, name = line.split('|')
            user_names[int(uid)] = name

    # 4. Compare
    discrepancies = []
    for uid in sorted(set(account_data.keys()) | set(accounting_data.keys())):
        acct_bal = account_data.get(uid, 0)
        accting_bal = accounting_data.get(uid, 0)
        diff = acct_bal - accting_bal
        name = user_names.get(uid, f"User {uid}")
        
        if abs(diff) > 1:  # tolerance of Rp 1
            discrepancies.append({
                "user": name,
                "user_id": uid,
                "account_balance": acct_bal,
                "accounting_balance": accting_bal,
                "difference": diff
            })

    # 5. Output
    if not discrepancies:
        # Silent success - no output means nothing to report
        print("OK: Semua saldo akun dan akunting sinkron.")
    else:
        print("⚠️ REKONSILIASI AKUN vs AKUNTING")
        print("=" * 40)
        for d in discrepancies:
            direction = "lebih besar" if d["difference"] > 0 else "lebih kecil"
            print(f"\n👤 {d['user']} (ID {d['user_id']}):")
            print(f"  💰 Saldo Akun:    Rp {d['account_balance']:,.0f}")
            print(f"  📊 Sisa Akunting: Rp {d['accounting_balance']:,.0f}")
            print(f"  ⚠️ Selisih: Rp {abs(d['difference']):,.0f} ({direction})")
        print("\n" + "=" * 40)
        print("Aksi diperlukan: tambah adjustment transaction.")

if __name__ == "__main__":
    main()
