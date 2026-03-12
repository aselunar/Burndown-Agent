/**
 * FILE STORAGE SYSTEM — all 4 levels in one class.
 *
 * LEVEL TRANSITION ROADMAP:
 *   L1 → L2: add FILE_SEARCH (prefix filter, sort by size DESC then name ASC, top 10)
 *   L2 → L3: refactor files map to store { size, uploadedAt, expiresAt }
 *             add *_AT variants; every _AT op must filter expired files
 *   L3 → L4: snapshot state before each _AT op for ROLLBACK; recalculate TTLs on restore
 *
 * KEY DIFFERENCE vs. BankingSystem / InMemoryDB:
 *   FILE_UPLOAD throws (runtime exception) on duplicate — does NOT return "" or "false"
 *   FILE_COPY throws if source doesn't exist
 *   TTL unit: seconds (InMemoryDB uses milliseconds!)
 *
 * RETURN VALUE CHEAT SHEET:
 *   fileUpload   → throws on duplicate
 *   fileGet      → size (number) | undefined
 *   fileCopy     → throws if source missing; overwrites if dest exists
 *   fileSearch   → ["name(size)", ...] top 10 sorted size DESC, name ASC
 *   fileUploadAt → (void / stores file)
 *   fileGetAt    → size (number) | undefined
 *   fileCopyAt   → (void)
 *   fileSearchAt → ["name(size)", ...] excluding expired
 *   rollback     → (void) restores to state at given timestamp, recalcs TTLs
 */
class FileStorage {
  constructor() {
    // L1/L2: files map
    // L3: each entry → { size, uploadedAt, expiresAt }  (expiresAt = null → no TTL)
    this.files = new Map();

    // L4: ordered snapshots [ { timestamp, filesSnapshot } ]
    // snapshot saved AFTER each _AT operation so rollback can restore to that moment
    this.snapshots = [];
  }

  // ── helpers ──────────────────────────────────────────────────────────────

  // Returns true when file is alive at `ts` (no TTL or not yet expired)
  _isAlive(file, ts) {
    return file.expiresAt === null || ts < file.expiresAt;
  }

  // Deep-copy the files map for snapshotting
  _snapshot(timestamp) {
    const copy = new Map();
    for (const [name, f] of this.files) {
      copy.set(name, { ...f });
    }
    this.snapshots.push({ timestamp, files: copy });
  }

  // ── LEVEL 1 ──────────────────────────────────────────────────────────────

  fileUpload(fileName, size) {
    if (this.files.has(fileName)) throw new Error(`File already exists: ${fileName}`);
    this.files.set(fileName, { size, uploadedAt: null, expiresAt: null });
  }

  fileGet(fileName) {
    const f = this.files.get(fileName);
    return f ? f.size : undefined;
  }

  // Overwrites dest if it exists; throws if source is missing
  fileCopy(source, dest) {
    const src = this.files.get(source);
    if (!src) throw new Error(`Source file not found: ${source}`);
    this.files.set(dest, { ...src });
  }

  // ── LEVEL 2 ──────────────────────────────────────────────────────────────
  // Tricky sort: size DESC primary, fileName ASC secondary (not size ASC!)

  fileSearch(prefix) {
    return [...this.files.entries()]
      .filter(([name]) => name.startsWith(prefix))
      .sort((a, b) => b[1].size - a[1].size || a[0].localeCompare(b[0]))
      .slice(0, 10)
      .map(([name, f]) => `${name}(${f.size})`);
  }

  // ── LEVEL 3 ──────────────────────────────────────────────────────────────
  // TTL is in SECONDS. expiresAt = uploadedAt + ttl
  // A file is alive at timestamp T if T < expiresAt (expired AT expiresAt exactly)

  fileUploadAt(timestamp, fileName, size, ttl = null) {
    // Overwrite if already exists (no throw for _AT variant when dest exists on copy,
    // but fileUploadAt itself follows same "throw on duplicate" semantics per spec)
    if (this.files.has(fileName)) throw new Error(`File already exists: ${fileName}`);
    const expiresAt = ttl !== null ? timestamp + ttl : null;
    this.files.set(fileName, { size, uploadedAt: timestamp, expiresAt });
    this._snapshot(timestamp);
  }

  fileGetAt(timestamp, fileName) {
    const f = this.files.get(fileName);
    if (!f || !this._isAlive(f, timestamp)) return undefined;
    return f.size;
  }

  fileCopyAt(timestamp, source, dest) {
    const src = this.files.get(source);
    if (!src || !this._isAlive(src, timestamp)) throw new Error(`Source not found or expired: ${source}`);
    // dest may or may not exist; overwrite is OK
    this.files.set(dest, { size: src.size, uploadedAt: timestamp, expiresAt: src.expiresAt });
    this._snapshot(timestamp);
  }

  fileSearchAt(timestamp, prefix) {
    return [...this.files.entries()]
      .filter(([name, f]) => name.startsWith(prefix) && this._isAlive(f, timestamp))
      .sort((a, b) => b[1].size - a[1].size || a[0].localeCompare(b[0]))
      .slice(0, 10)
      .map(([name, f]) => `${name}(${f.size})`);
  }

  // ── LEVEL 4 ──────────────────────────────────────────────────────────────
  // ROLLBACK(ts): restore the LATEST snapshot with snapshot.timestamp <= ts
  //   TTL recalc: newExpiresAt = rollbackCallTimestamp + (oldExpiresAt - snapshotTimestamp)
  //   Files with no TTL keep no TTL; files already expired at ts are excluded.

  rollback(timestamp) {
    // Find most recent snapshot at or before timestamp
    let target = null;
    for (let i = this.snapshots.length - 1; i >= 0; i--) {
      if (this.snapshots[i].timestamp <= timestamp) {
        target = this.snapshots[i];
        break;
      }
    }
    if (!target) return; // no snapshot before this timestamp — nothing to restore

    const snapshotTs = target.timestamp;
    this.files = new Map();

    for (const [name, f] of target.files) {
      // Skip files that were already expired at the snapshot timestamp
      if (!this._isAlive(f, snapshotTs)) continue;

      let newExpiresAt = null;
      if (f.expiresAt !== null) {
        // Preserve remaining TTL relative to the snapshot moment
        newExpiresAt = timestamp + (f.expiresAt - snapshotTs);
      }
      this.files.set(name, { size: f.size, uploadedAt: f.uploadedAt, expiresAt: newExpiresAt });
    }
  }
}

module.exports = FileStorage;
