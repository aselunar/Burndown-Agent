/**
 * BANKING SYSTEM — all 4 levels in one class.
 *
 * LEVEL TRANSITION ROADMAP:
 *   L1 → L2: add outgoing + history tracking inside withdraw/transfer
 *   L2 → L3: add _processScheduled() call at the TOP of every mutating method;
 *             large amounts (>1000) return a payment_id instead of completing
 *   L3 → L4: mergeAccounts transfers balance + history + outgoing + scheduled + pending
 *
 * RETURN VALUE CHEAT SHEET (burn this in):
 *   createAccount  → "true" | "false"          (string booleans!)
 *   deposit        → balance string | ""
 *   withdraw       → balance string | payment_id | ""
 *   transfer       → src balance string | payment_id | ""
 *   topSpenders    → "id(amount), id(amount)" | ""
 *   schedulePayment → "true" | ""
 *   acceptPayment  → balance string | ""
 *   mergeAccounts  → acc1 balance string | ""
 *   getBankStats   → "total_accounts:N,total_balance:N,average_balance:N"
 *   cashback       → cashback amount string | ""
 */
class BankingSystem {
  constructor() {
    // L1 — core state
    this.accounts = new Map(); // accountId → { balance, createdAt }

    // L2 — query tracking (add tracking calls inside withdraw/transfer)
    this.outgoing = new Map(); // accountId → total outgoing (withdraw + transfer_out)
    this.history  = new Map(); // accountId → [{ type, amount }]  (append-only)

    // L3 — scheduled + pending approval
    this.scheduled      = []; // [{ executeAt, accountId, amount, type }]
    this.pending        = new Map(); // referenceId → { accountId, targetId, amount, type }
    this.paymentCounter = 0;
  }

  // ── helpers ──────────────────────────────────────────────────────────────

  _record(accountId, type, amount) {
    if (!this.history.has(accountId)) this.history.set(accountId, []);
    this.history.get(accountId).push({ type, amount });
  }

  _addOutgoing(accountId, amount) {
    this.outgoing.set(accountId, (this.outgoing.get(accountId) || 0) + amount);
  }

  // L3: must call at the TOP of every mutating public method.
  // Scheduled jobs fire in chronological order BEFORE the current op.
  _processScheduled(timestamp) {
    this.scheduled.sort((a, b) => a.executeAt - b.executeAt);
    while (this.scheduled.length && this.scheduled[0].executeAt <= timestamp) {
      const job = this.scheduled.shift();
      const acc = this.accounts.get(job.accountId);
      if (!acc) continue; // account may have been deleted/merged
      if (job.type === 'DEPOSIT') {
        acc.balance += job.amount;
        this._record(job.accountId, 'DEPOSIT', job.amount);
      } else if (job.type === 'WITHDRAW' && acc.balance >= job.amount) {
        acc.balance -= job.amount;
        this._record(job.accountId, 'WITHDRAW', job.amount);
        this._addOutgoing(job.accountId, job.amount);
      }
    }
  }

  // ── LEVEL 1 ──────────────────────────────────────────────────────────────

  createAccount(timestamp, accountId) {
    if (this.accounts.has(accountId)) return 'false';
    // Store createdAt for audit trail even if not queried by current levels
    this.accounts.set(accountId, { balance: 0, createdAt: timestamp });
    return 'true';
  }

  deposit(timestamp, accountId, amount) {
    this._processScheduled(timestamp);
    const acc = this.accounts.get(accountId);
    if (!acc) return '';
    acc.balance += amount;
    this._record(accountId, 'DEPOSIT', amount);
    return String(acc.balance);
  }

  withdraw(timestamp, accountId, amount) {
    this._processScheduled(timestamp);
    const acc = this.accounts.get(accountId);
    if (!acc) return '';
    if (acc.balance < amount) return '';
    // L3: amounts > 1000 require ACCEPT_PAYMENT — return reference id, NOT balance
    if (amount > 1000) {
      const refId = `payment_${++this.paymentCounter}`;
      this.pending.set(refId, { accountId, targetId: null, amount, type: 'WITHDRAW' });
      return refId;
    }
    acc.balance -= amount;
    this._record(accountId, 'WITHDRAW', amount);
    this._addOutgoing(accountId, amount);
    return String(acc.balance);
  }

  transfer(timestamp, srcId, tgtId, amount) {
    this._processScheduled(timestamp);
    const src = this.accounts.get(srcId);
    const tgt = this.accounts.get(tgtId);
    if (!src || !tgt) return '';
    if (src.balance < amount) return '';
    // L3: same large-amount guard as withdraw
    if (amount > 1000) {
      const refId = `payment_${++this.paymentCounter}`;
      this.pending.set(refId, { accountId: srcId, targetId: tgtId, amount, type: 'TRANSFER' });
      return refId;
    }
    src.balance -= amount;
    tgt.balance += amount;
    this._record(srcId, 'TRANSFER_OUT', amount);
    this._record(tgtId, 'TRANSFER_IN', amount);
    this._addOutgoing(srcId, amount);
    return String(src.balance);
  }

  // ── LEVEL 2 ──────────────────────────────────────────────────────────────
  // Tricky sort: primary = outgoing DESC, secondary = accountId ASC (lexicographic)

  topSpenders(timestamp, n) {
    this._processScheduled(timestamp);
    return [...this.outgoing.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, n)
      .map(([id, total]) => `${id}(${total})`)
      .join(', ');
  }

  // History is append-only → slice from the end, then reverse for "most recent first"
  getPaymentHistory(timestamp, accountId, n) {
    this._processScheduled(timestamp);
    if (!this.accounts.has(accountId)) return '';
    const hist = this.history.get(accountId) || [];
    return hist
      .slice(-n)
      .reverse()
      .map(h => `${h.type}(${h.amount})`)
      .join(', ');
  }

  // ── LEVEL 3 ──────────────────────────────────────────────────────────────

  schedulePayment(timestamp, accountId, amount, paymentType, delay) {
    if (!this.accounts.has(accountId)) return '';
    this.scheduled.push({ executeAt: timestamp + delay, accountId, amount, type: paymentType });
    return 'true';
  }

  // Completes a pending large-amount transaction; checks balance again at acceptance time
  acceptPayment(timestamp, accountId, referenceId) {
    this._processScheduled(timestamp);
    const pend = this.pending.get(referenceId);
    if (!pend || pend.accountId !== accountId) return '';
    this.pending.delete(referenceId);

    const acc = this.accounts.get(pend.accountId);
    if (!acc) return '';

    if (pend.type === 'WITHDRAW') {
      if (acc.balance < pend.amount) return '';
      acc.balance -= pend.amount;
      this._record(pend.accountId, 'WITHDRAW', pend.amount);
      this._addOutgoing(pend.accountId, pend.amount);
      return String(acc.balance);
    }

    if (pend.type === 'TRANSFER') {
      const tgt = this.accounts.get(pend.targetId);
      if (!tgt || acc.balance < pend.amount) return '';
      acc.balance -= pend.amount;
      tgt.balance += pend.amount;
      this._record(pend.accountId, 'TRANSFER_OUT', pend.amount);
      this._record(pend.targetId, 'TRANSFER_IN', pend.amount);
      this._addOutgoing(pend.accountId, pend.amount);
      return String(acc.balance);
    }

    return '';
  }

  // Counts history entries + unexecuted scheduled + pending for each account
  topActivity(timestamp, n) {
    this._processScheduled(timestamp);
    const counts = new Map();
    for (const id of this.accounts.keys()) {
      const histCount  = (this.history.get(id) || []).length;
      const schedCount = this.scheduled.filter(s => s.accountId === id).length;
      const pendCount  = [...this.pending.values()].filter(p => p.accountId === id).length;
      counts.set(id, histCount + schedCount + pendCount);
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, n)
      .map(([id, c]) => `${id}(${c})`)
      .join(', ');
  }

  // ── LEVEL 4 ──────────────────────────────────────────────────────────────

  // Merge acc2 INTO acc1: balance + history + outgoing + scheduled + pending all transfer
  mergeAccounts(timestamp, accountId1, accountId2) {
    this._processScheduled(timestamp);
    const acc1 = this.accounts.get(accountId1);
    const acc2 = this.accounts.get(accountId2);
    if (!acc1 || !acc2) return '';

    acc1.balance += acc2.balance;

    // Merge history (keep chronological; both arrays already append-ordered)
    const h1 = this.history.get(accountId1) || [];
    const h2 = this.history.get(accountId2) || [];
    this.history.set(accountId1, [...h1, ...h2]);

    // Merge outgoing totals
    this.outgoing.set(
      accountId1,
      (this.outgoing.get(accountId1) || 0) + (this.outgoing.get(accountId2) || 0)
    );

    // Re-point scheduled and pending from acc2 → acc1
    for (const job of this.scheduled) {
      if (job.accountId === accountId2) job.accountId = accountId1;
    }
    for (const pend of this.pending.values()) {
      if (pend.accountId === accountId2) pend.accountId = accountId1;
      if (pend.targetId  === accountId2) pend.targetId  = accountId1;
    }

    this.accounts.delete(accountId2);
    this.history.delete(accountId2);
    this.outgoing.delete(accountId2);
    return String(acc1.balance);
  }

  // average_balance = Math.floor(total / count)  ← floor, not round
  getBankStatistics(timestamp) {
    this._processScheduled(timestamp);
    const balances = [...this.accounts.values()].map(a => a.balance);
    const total    = balances.reduce((s, b) => s + b, 0);
    const avg      = balances.length ? Math.floor(total / balances.length) : 0;
    return `total_accounts:${balances.length},total_balance:${total},average_balance:${avg}`;
  }

  // cashback = Math.floor(totalOutgoing * pct / 100); returns "" if no spending
  cashback(timestamp, accountId, percentage) {
    this._processScheduled(timestamp);
    const acc = this.accounts.get(accountId);
    if (!acc) return '';
    const spent = this.outgoing.get(accountId) || 0;
    if (spent === 0) return '';
    const reward = Math.floor(spent * percentage / 100);
    acc.balance += reward;
    return String(reward);
  }
}

module.exports = BankingSystem;
