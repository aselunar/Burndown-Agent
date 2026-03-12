# CodeSignal Progressive Assessment — Memorization Guide

Three problems, four levels each. Study this before your OA.

---

## Quick-Reference: Return Value Cheat Sheet

> **Burn this table into memory — wrong return format = wrong answer.**

| Problem | Operation | Returns on success | Returns on failure |
|---------|-----------|-------------------|-------------------|
| **Bank** | createAccount | `"true"` | `"false"` |
| **Bank** | deposit | balance string | `""` |
| **Bank** | withdraw (≤1000) | balance string | `""` |
| **Bank** | withdraw (>1000) | `"payment_N"` | `""` |
| **Bank** | transfer (≤1000) | src balance string | `""` |
| **Bank** | transfer (>1000) | `"payment_N"` | `""` |
| **Bank** | topSpenders | `"id(amt), id(amt)"` | `""` (no spenders) |
| **Bank** | schedulePayment | `"true"` | `""` |
| **Bank** | acceptPayment | balance string | `""` |
| **Bank** | mergeAccounts | acc1 balance string | `""` |
| **Bank** | getBankStatistics | `"total_accounts:N,total_balance:N,average_balance:N"` | — |
| **Bank** | cashback | cashback amount string | `""` |
| **File** | fileUpload | void | **throws** (not `""`) |
| **File** | fileGet | size (number) | `undefined` |
| **File** | fileCopy | void | **throws** if src missing |
| **File** | fileSearch | `["name(size)", ...]` array | `[]` |
| **DB** | setField / setFieldAt | value string | — |
| **DB** | getField / getFieldAt | value string | `""` |
| **DB** | deleteField | `"true"` | `"false"` |
| **DB** | get / getAt | `"f(v), f(v)"` sorted α | `""` |
| **DB** | scan / scanAt | `"k1, k2"` sorted α | `""` |
| **DB** | delete (whole key) | `"true"` | `"false"` |
| **DB** | topNKeys | `"key(N), key(N)"` | `""` |
| **DB** | backup | `"backup_N"` | — |
| **DB** | restore | keys-restored count string | `""` |
| **DB** | compare | `"k1, k2"` sorted α | `""` |
| **DB** | getBackupInfo | `"keys:N,fields:N,timestamp:N"` | `""` |

---

## Sort Rules Cheat Sheet

| Operation | Primary Sort | Tie-Break |
|-----------|-------------|-----------|
| topSpenders | outgoing DESC | accountId ASC (α) |
| topActivity | transaction count DESC | accountId ASC (α) |
| topNKeys | field count DESC | key name ASC (α) |
| fileSearch / fileSearchAt | size DESC | file name ASC (α) |
| scan / scanAt | — | key ASC (α) |
| scanByField / compare | — | key ASC (α) |
| get / getAt | — | field name ASC (α) |

---

## Problem 1: Banking System

### State You Need

```
accounts  Map<id, { balance, createdAt }>   // createdAt stored for audit trail
outgoing  Map<id, number>                   // L2: WITHDRAW + TRANSFER_OUT only
history   Map<id, [{ type, amount }]>       // L2: append-only, most-recent = last
scheduled []  // L3: { executeAt, accountId, amount, type }
pending   Map<refId, { accountId, targetId, amount, type }>  // L3
paymentCounter  number                      // L3: sequential ID counter
```

### Level-by-Level Operations

| Level | New Operations | Key Change |
|-------|----------------|------------|
| L1 | createAccount, deposit, withdraw, transfer | Basic Map ops |
| L2 | topSpenders, getPaymentHistory | Add outgoing/history tracking inside withdraw/transfer |
| L3 | schedulePayment, acceptPayment, topActivity | Process scheduled at top of every op; withdraw/transfer >1000 → pending |
| L4 | mergeAccounts, getBankStatistics, cashback | Merge ALL state (balance, history, outgoing, scheduled, pending) |

### Edge Cases to Memorize

- `transfer` to self: source == target — spec doesn't explicitly forbid it, but check funds once
- `mergeAccounts`: both accounts must exist; re-point scheduled + pending from acc2 → acc1
- `cashback`: returns `""` if no spending (outgoing = 0), even if account exists
- `getBankStatistics`: `average = Math.floor(total / count)` — floor, not round
- `topSpenders`: only accounts with outgoing > 0 appear; returns `""` if none
- Scheduled payments that fail (insufficient funds for WITHDRAW) are silently skipped
- `getPaymentHistory` returns `""` for an account with zero transactions (existing account, no operations yet)

### L1 → L2 Transition Checklist
- [ ] Add `_record(accountId, type, amount)` helper
- [ ] Add `_addOutgoing(accountId, amount)` helper
- [ ] Call `_record` in deposit (DEPOSIT), withdraw (WITHDRAW), transfer (TRANSFER_OUT on src, TRANSFER_IN on tgt)
- [ ] Call `_addOutgoing` in withdraw and transfer (src side only)

### L2 → L3 Transition Checklist
- [ ] Add `_processScheduled(timestamp)` — sort by executeAt, fire all ≤ timestamp
- [ ] Call `_processScheduled(timestamp)` at the **TOP** of every public method that takes a timestamp
- [ ] In withdraw/transfer: check `amount > 1000` → create pending entry, return payment_id

### L3 → L4 Transition Checklist
- [ ] mergeAccounts: combine balance, concat history arrays, sum outgoing, re-point scheduled + pending
- [ ] getBankStatistics: only active (non-merged) accounts
- [ ] cashback: look up outgoing map, floor the percentage

---

## Problem 2: File Storage System

### State You Need

```
files     Map<name, { size, uploadedAt, expiresAt }>
          // expiresAt = null means no TTL (lives forever)
snapshots []  // L4: [{ timestamp, files: Map copy }]
```

### Level-by-Level Operations

| Level | New Operations | Key Change |
|-------|----------------|------------|
| L1 | fileUpload, fileGet, fileCopy | Basic Map; **throws** on errors |
| L2 | fileSearch | Prefix filter, sort size DESC + name ASC, top 10 |
| L3 | fileUploadAt, fileGetAt, fileCopyAt, fileSearchAt | Add TTL support; refactor file entry to include expiresAt |
| L4 | rollback | Snapshot after every _AT op; restore latest snapshot ≤ timestamp; recalc TTLs |

### File Storage vs. InMemoryDB Differences

| Aspect | File Storage | In-Memory DB |
|--------|-------------|--------------|
| Error on duplicate upload | **throws** | N/A (setField overwrites) |
| Missing key/file | returns `undefined` | returns `""` |
| TTL unit | **seconds** | **milliseconds** |
| State restore | ROLLBACK by timestamp | RESTORE by backup_id |

### TTL Formula (SAME for both problems)
```
expiresAt = uploadTimestamp + ttl
isAlive(T) = T < expiresAt          // expired AT the exact expiry moment
```

### TTL Recalculation on Rollback / Restore
```
newExpiresAt = callTimestamp + (oldExpiresAt - snapshotTimestamp)
```
This preserves the remaining TTL as it was at the snapshot/backup time.

### Edge Cases to Memorize

- `fileUpload` **throws**, does NOT return `""` — this is unique to File Storage
- `fileCopy` **throws** if source missing; silently **overwrites** if dest exists
- `fileSearch` returns top **10** (not all), filtered by prefix
- `rollback` with no matching snapshot → do nothing (no-op)
- After rollback, files expired at the snapshot time are excluded
- `fileCopyAt` propagates the source's `expiresAt` to the destination

### L2 → L3 Transition Checklist
- [ ] Refactor `files` entries to `{ size, uploadedAt, expiresAt }`
- [ ] Add `_isAlive(file, ts)` helper
- [ ] All `_AT` methods filter by `_isAlive` before operating

### L3 → L4 Transition Checklist
- [ ] Add `_snapshot(timestamp)` — deep-copy files map, push to snapshots
- [ ] Call `_snapshot` at end of each mutating `_AT` method
- [ ] `rollback(ts)`: find latest snapshot where snapshot.timestamp ≤ ts; rebuild files; recalc TTLs

---

## Problem 3: In-Memory Database

### State You Need

```
db       Map<key, Map<field, { value, expiresAt }>>
         // expiresAt = null means no TTL
backups  Map<"backup_N", { timestamp, data: deep copy of db }>
backupCounter  number
```

### Level-by-Level Operations

| Level | New Operations | Key Change |
|-------|----------------|------------|
| L1 | setField, getField, deleteField, get | Nested Map; auto-prune empty keys |
| L2 | scan, scanByField, delete, topNKeys | Prefix scan, whole-key delete |
| L3 | setFieldAt, setFieldWithTtl, getFieldAt, getAt, deleteFieldAt, scanAt, scanByFieldAt | Add expiresAt to field entries |
| L4 | backup, restore, compare, getBackupInfo | Snapshot non-expired fields; TTL recalc on restore |

### Key Pruning Rule
```
After any deleteField: if the key has 0 fields remaining → delete the key itself.
Applies to both L1 deleteField and L3 deleteFieldAt.
```

### Edge Cases to Memorize

- `deleteField` on last field → removes the key entirely
- `scan` returns `""` (empty string), NOT `[]` array
- `topNKeys`: counts fields per key; empty keys have already been pruned
- `setFieldWithTtl` — field is unavailable AT `expiresAt` (not after)
- `backup` only snapshots fields alive at the backup timestamp
- `restore` returns count of **keys** restored (as a string), not fields
- `compare` returns `""` if either backup doesn't exist (not an error throw)
- TTL unit: **milliseconds** (NOT seconds like File Storage)

### L1 → L2 Transition Checklist
- [ ] `scan(prefix)` — filter `db.keys()` by startsWith, sort, join(', ')
- [ ] `scanByField(field, value)` — iterate all keys, check if field exists and matches
- [ ] `delete(key)` — delete entire key, return "true"/"false"
- [ ] `topNKeys(n)` — sort by fields.size DESC, then key α

### L2 → L3 Transition Checklist
- [ ] Field storage: `{ value: string }` → `{ value: string, expiresAt: number | null }`
- [ ] Add `_isFieldAlive(entry, ts)` and `_aliveFields(key, ts)` helpers
- [ ] Every read operation (`getFieldAt`, `getAt`, `scanAt`, `scanByFieldAt`) must filter alive fields
- [ ] `scanAt`: skip keys where `_aliveFields(k, ts).length === 0`

### L3 → L4 Transition Checklist
- [ ] `backup(ts)`: deep-copy only alive fields → store with timestamp
- [ ] `restore(ts, id)`: replace `this.db` entirely; for each field, if expiresAt !== null → `ts + (expiresAt - bk.timestamp)`
- [ ] `compare`: check all keys in union of both backups; differ if missing in one, or field values differ

---

## Algorithmic Transitions Summary

```
                L1          L2              L3                  L4
Bank     CRUD ops    +query/sort     +scheduled/pending    +merge/stats/cashback
File     CRUD+throw  +search/sort    +TTL timestamps       +rollback snapshots
DB       nested CRUD +prefix scan    +TTL fields           +backup/restore/compare
```

**What changes between each level:**
- **L1→L2**: Add aggregation/query operations. Requires tracking extra state during L1 mutations.
- **L2→L3**: Add time awareness. Requires refactoring data model (add TTL fields) + pre-processing at each op.
- **L3→L4**: Add durability/recovery. Requires snapshot mechanics + TTL recalculation math.

---

## Drill Sequences

### 5-Minute Recall Drill (per problem)
1. Write the class constructor (state only, no methods)
2. Write the method signatures for all 4 levels from memory
3. Implement level 1 operations only
4. Add level 2 operations; check what new state you needed to add in L1
5. Add level 3 changes; identify what L1/L2 methods need to be modified

### Edge Case Flash Cards

**Card 1:** What does `withdraw("acc", 2000)` return when balance is 500?
→ `""` (insufficient funds — empty string, not "false")

**Card 2:** What does `fileUpload("file.txt", 100)` do if file.txt already exists?
→ **Throws** a runtime exception (NOT returns "" or "false")

**Card 3:** `setFieldWithTtl(10, "k", "f", "v", 20)` — is the field available at t=30?
→ No. `expiresAt = 10+20 = 30`. Field is unavailable AT 30. `getFieldAt(30, ...)` returns `""`.

**Card 4:** What does `topSpenders` return when no account has spent anything?
→ `""` (empty string — accounts with zero outgoing don't appear)

**Card 5:** `mergeAccounts("a", "b")` — which account survives?
→ `"a"` survives. `"b"` is deleted. All of b's state transfers to a.

**Card 6:** `cashback("acc", 5)` when account has made no withdrawals or transfers?
→ `""` (not 0, not "0" — empty string because no spending)

**Card 7:** What's the TTL recalculation formula for restore/rollback?
→ `newExpiresAt = callTimestamp + (oldExpiresAt - snapshotTimestamp)`

**Card 8:** `fileSearch("doc")` — what's the sort order?
→ Size **DESC** primary; file name **ASC** secondary (alphabetical). Returns top **10**.

**Card 9:** What does `deleteField` return when deleting the last field of a key?
→ `"true"` (deletion succeeded). The key itself is also removed.

**Card 10:** `restore(50, "backup_1")` — what does it return?
→ The number of keys restored, as a **string** (e.g., `"3"`).

---

## Avoiding Confusion Between the Three Problems

| Question | Bank | File | DB |
|----------|------|------|----|
| Error on missing resource | `""` | throws | `""` |
| Duplicate write | `"false"` | throws | overwrites |
| TTL unit | N/A | **seconds** | **milliseconds** |
| "Restore to past" mechanism | N/A | ROLLBACK(timestamp) | RESTORE(timestamp, id) |
| Aggregation query | topSpenders | fileSearch | topNKeys |
| Primary sort key | outgoing DESC | size DESC | field-count DESC |
| Output of query operations | `"id(val)"` comma-sep string | `["name(size)"]` array | `"key(N)"` comma-sep string |

---

## Spaced Repetition Workflow

### Recommended Tools
- **Anki** (free): Best for flash cards. Create a deck per problem, one card per edge case.
- **RemNote**: Supports hierarchical notes with built-in spaced repetition.
- **Notion + Recall plugin**: If you prefer a doc-based approach.

### Anki Card Template
```
Front: [Problem] [Level] — [operation name]
       "What does X return when Y?"

Back:  Return value + one-line explanation of the edge case
       + "Gotcha: [tricky part]"
```

### Study Schedule (7 days before OA)
| Day | Focus |
|-----|-------|
| Day 7 | Read all level specs. Set up project. Make sure tests run. |
| Day 6 | Implement Banking System L1+L2 from scratch (no reference). Run tests. |
| Day 5 | Banking System L3+L4 from scratch. Run tests. |
| Day 4 | File Storage all 4 levels from scratch. Run tests. |
| Day 3 | In-Memory DB all 4 levels from scratch. Run tests. |
| Day 2 | Full timed run: all 3 problems, 90-minute timer. Note what tripped you up. |
| Day 1 | Review edge cases only. Read this guide. Drill flash cards. Sleep early. |

---

## Test Day Checklist

### Before You Start
- [ ] Read the full problem statement (all 4 levels) before writing any code
- [ ] Note the exact return type for each operation (string "true" not boolean true)
- [ ] Check if errors throw vs. return "" (File Storage throws; the other two return "")
- [ ] Confirm TTL unit from the spec (seconds vs. milliseconds)

### When Implementing
- [ ] L1: Build the simplest working version — don't over-engineer
- [ ] L2: Check if you need to add tracking state that should have been in L1 already
- [ ] L3: Add `_processScheduled` / TTL check helper first, then update each method
- [ ] L4: Snapshot/backup before implementing restore — get the data model right

### Submission Strategy
- Press "Submit" after completing each level — partial credit is awarded
- Don't skip to later levels trying to be clever; complete each level fully before moving on
- Test your sort order: DESC/ASC mix-ups are the most common source of wrong answers

### Common Mistakes Checklist
- [ ] Returning `false` (boolean) instead of `"false"` (string)
- [ ] Not calling `_processScheduled` at the top of every method in L3
- [ ] Including TRANSFER_IN in `outgoing` (it should only be TRANSFER_OUT)
- [ ] Sorting file results by size ASC instead of DESC
- [ ] Using `Math.round` instead of `Math.floor` for average/cashback
- [ ] Forgetting to prune the key after deleting the last field (InMemoryDB)
- [ ] Not recalculating TTL when doing restore/rollback
