/**
 * IN-MEMORY DATABASE — all 4 levels in one class.
 *
 * LEVEL TRANSITION ROADMAP:
 *   L1 → L2: add SCAN, SCAN_BY_FIELD, DELETE (whole key), TOP_N_KEYS
 *   L2 → L3: refactor field storage to { value, expiresAt }
 *             add *_AT / *_WITH_TTL variants; all reads must check expiry
 *   L3 → L4: add BACKUP (snapshot non-expired fields), RESTORE (recalc TTLs), COMPARE
 *
 * KEY DIFFERENCE vs. Banking/FileStorage:
 *   TTL unit: MILLISECONDS (FileStorage uses seconds!)
 *   field expired at T: timestamp >= (setTimestamp + ttl)  i.e., unavailable AT expiresAt
 *
 * RETURN VALUE CHEAT SHEET:
 *   setField      → value string set
 *   getField      → value string | ""
 *   deleteField   → "true" | "false"
 *   get           → "field(val), field(val)" sorted α | ""
 *   scan          → "key1, key2" sorted α | ""
 *   scanByField   → "key1, key2" sorted α | ""
 *   delete        → "true" | "false"
 *   topNKeys      → "key(count), key(count)" desc count, α tie-break | ""
 *   backup        → "backup_N"
 *   restore       → keys-restored count as string | ""
 *   compare       → "key1, key2" sorted α | ""
 *   getBackupInfo → "keys:N,fields:N,timestamp:N" | ""
 */
class InMemoryDatabase {
  constructor() {
    // L1/L2: db[key][field] = value (string)
    // L3: db[key][field] = { value, expiresAt }  (expiresAt = null → no TTL)
    this.db = new Map();

    // L4: backup storage
    this.backups = new Map(); // "backup_N" → { timestamp, data: Map<key, Map<field, {value, expiresAt}>> }
    this.backupCounter = 0;
  }

  // ── helpers ──────────────────────────────────────────────────────────────

  _isFieldAlive(entry, ts) {
    return entry.expiresAt === null || ts < entry.expiresAt;
  }

  // Returns an iterable of [field, entry] pairs that are alive at ts
  _aliveFields(key, ts) {
    const fields = this.db.get(key);
    if (!fields) return [];
    return [...fields.entries()].filter(([, e]) => this._isFieldAlive(e, ts));
  }

  // Remove key entirely if it has no more fields (called after any deletion)
  _pruneKey(key) {
    const fields = this.db.get(key);
    if (fields && fields.size === 0) this.db.delete(key);
  }

  // ── LEVEL 1 ──────────────────────────────────────────────────────────────

  setField(key, field, value) {
    if (!this.db.has(key)) this.db.set(key, new Map());
    this.db.get(key).set(field, { value, expiresAt: null });
    return value;
  }

  getField(key, field) {
    const fields = this.db.get(key);
    if (!fields) return '';
    const entry = fields.get(field);
    if (!entry) return '';
    return entry.value;
  }

  deleteField(key, field) {
    const fields = this.db.get(key);
    if (!fields || !fields.has(field)) return 'false';
    fields.delete(field);
    this._pruneKey(key);
    return 'true';
  }

  // Fields sorted alphabetically in output
  get(key) {
    const fields = this.db.get(key);
    if (!fields || fields.size === 0) return '';
    return [...fields.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([f, e]) => `${f}(${e.value})`)
      .join(', ');
  }

  // ── LEVEL 2 ──────────────────────────────────────────────────────────────

  // Only include keys with ≥1 field; keys with 0 fields were already pruned
  scan(prefix) {
    return [...this.db.keys()]
      .filter(k => k.startsWith(prefix) && this.db.get(k).size > 0)
      .sort()
      .join(', ');
  }

  scanByField(field, value) {
    return [...this.db.entries()]
      .filter(([, fields]) => {
        const entry = fields.get(field);
        return entry && entry.value === value;
      })
      .map(([k]) => k)
      .sort()
      .join(', ');
  }

  // Deletes the entire key (all fields)
  delete(key) {
    if (!this.db.has(key)) return 'false';
    this.db.delete(key);
    return 'true';
  }

  // Sort by field-count DESC, then key name ASC
  topNKeys(n) {
    return [...this.db.entries()]
      .filter(([, fields]) => fields.size > 0)
      .sort((a, b) => b[1].size - a[1].size || a[0].localeCompare(b[0]))
      .slice(0, n)
      .map(([k, fields]) => `${k}(${fields.size})`)
      .join(', ');
  }

  // ── LEVEL 3 ──────────────────────────────────────────────────────────────
  // TTL in MILLISECONDS. expiresAt = timestamp + ttl
  // Field is expired at timestamp >= expiresAt (unavailable AT the expiry moment)

  setFieldAt(timestamp, key, field, value) {
    if (!this.db.has(key)) this.db.set(key, new Map());
    this.db.get(key).set(field, { value, expiresAt: null });
    return value;
  }

  setFieldWithTtl(timestamp, key, field, value, ttl) {
    if (!this.db.has(key)) this.db.set(key, new Map());
    this.db.get(key).set(field, { value, expiresAt: timestamp + ttl });
    return value;
  }

  getFieldAt(timestamp, key, field) {
    const fields = this.db.get(key);
    if (!fields) return '';
    const entry = fields.get(field);
    if (!entry || !this._isFieldAlive(entry, timestamp)) return '';
    return entry.value;
  }

  getAt(timestamp, key) {
    const alive = this._aliveFields(key, timestamp);
    if (alive.length === 0) return '';
    return alive
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([f, e]) => `${f}(${e.value})`)
      .join(', ');
  }

  deleteFieldAt(timestamp, key, field) {
    const fields = this.db.get(key);
    if (!fields) return 'false';
    const entry = fields.get(field);
    if (!entry || !this._isFieldAlive(entry, timestamp)) return 'false';
    fields.delete(field);
    this._pruneKey(key);
    return 'true';
  }

  // Only return keys with ≥1 alive field at timestamp
  scanAt(timestamp, prefix) {
    return [...this.db.entries()]
      .filter(([k]) => k.startsWith(prefix))
      .filter(([k]) => this._aliveFields(k, timestamp).length > 0)
      .map(([k]) => k)
      .sort()
      .join(', ');
  }

  scanByFieldAt(timestamp, field, value) {
    return [...this.db.entries()]
      .filter(([k]) => {
        const entry = this.db.get(k).get(field);
        return entry && this._isFieldAlive(entry, timestamp) && entry.value === value;
      })
      .map(([k]) => k)
      .sort()
      .join(', ');
  }

  // ── LEVEL 4 ──────────────────────────────────────────────────────────────

  // Snapshot only alive fields; returns "backup_N"
  backup(timestamp) {
    const id = `backup_${++this.backupCounter}`;
    const data = new Map();
    for (const [key, fields] of this.db) {
      const alive = this._aliveFields(key, timestamp);
      if (alive.length === 0) continue;
      const fieldsCopy = new Map();
      for (const [f, e] of alive) {
        fieldsCopy.set(f, { value: e.value, expiresAt: e.expiresAt });
      }
      data.set(key, fieldsCopy);
    }
    this.backups.set(id, { timestamp, data });
    return id;
  }

  // Restore: recalculate TTLs so remaining lifetime is preserved.
  // Formula: newExpiresAt = restoreTimestamp + (oldExpiresAt - backupTimestamp)
  restore(timestamp, backupId) {
    const bk = this.backups.get(backupId);
    if (!bk) return '';

    this.db = new Map();
    for (const [key, fields] of bk.data) {
      const newFields = new Map();
      for (const [f, e] of fields) {
        let newExpiresAt = null;
        if (e.expiresAt !== null) {
          newExpiresAt = timestamp + (e.expiresAt - bk.timestamp);
        }
        newFields.set(f, { value: e.value, expiresAt: newExpiresAt });
      }
      this.db.set(key, newFields);
    }
    return String(bk.data.size);
  }

  // Compare two backup snapshots; return keys that differ (exist in one but not both, or have different fields)
  compare(backupId1, backupId2) {
    const bk1 = this.backups.get(backupId1);
    const bk2 = this.backups.get(backupId2);
    if (!bk1 || !bk2) return '';

    const allKeys = new Set([...bk1.data.keys(), ...bk2.data.keys()]);
    const diffKeys = [];

    for (const key of allKeys) {
      const fields1 = bk1.data.get(key);
      const fields2 = bk2.data.get(key);
      if (!fields1 || !fields2) {
        diffKeys.push(key);
        continue;
      }
      // Compare field names + values (not expiresAt — compare logical content)
      if (fields1.size !== fields2.size) {
        diffKeys.push(key);
        continue;
      }
      let differs = false;
      for (const [f, e] of fields1) {
        const e2 = fields2.get(f);
        if (!e2 || e2.value !== e.value) { differs = true; break; }
      }
      if (differs) diffKeys.push(key);
    }

    return diffKeys.sort().join(', ');
  }

  getBackupInfo(backupId) {
    const bk = this.backups.get(backupId);
    if (!bk) return '';
    let totalFields = 0;
    for (const fields of bk.data.values()) totalFields += fields.size;
    return `keys:${bk.data.size},fields:${totalFields},timestamp:${bk.timestamp}`;
  }
}

module.exports = InMemoryDatabase;
