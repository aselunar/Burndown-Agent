const InMemoryDatabase = require('./inMemoryDatabase');

// LEVEL 4 — BACKUP, RESTORE, COMPARE, GET_BACKUP_INFO
// KEY TRANSITIONS FROM L3:
//   • BACKUP snapshots only alive (non-expired) fields at the given timestamp
//   • RESTORE replaces current db with backup data; recalculates TTLs:
//       newExpiresAt = restoreTimestamp + (oldExpiresAt - backupTimestamp)
//     Fields with no TTL remain without TTL.
//   • COMPARE finds keys that differ between two backups (missing in one, or value differs)
//   • Backup IDs are sequential: "backup_1", "backup_2", ...

describe('In-Memory Database — Level 4', () => {
  let db;

  beforeEach(() => {
    db = new InMemoryDatabase();
  });

  describe('backup', () => {
    test('returns sequential backup IDs starting from backup_1', () => {
      db.setFieldAt(10, 'k', 'f', 'v');
      expect(db.backup(10)).toBe('backup_1');
      expect(db.backup(20)).toBe('backup_2');
    });

    test('backup captures only alive fields at backup timestamp', () => {
      db.setFieldWithTtl(10, 'k', 'temp', 'x', 5); // expires at t=15
      db.setFieldAt(10, 'k', 'perm', 'y');
      const id = db.backup(20); // temp is expired at t=20
      // restore and verify only perm is there
      db.restore(30, id);
      expect(db.getFieldAt(30, 'k', 'perm')).toBe('y');
      expect(db.getFieldAt(30, 'k', 'temp')).toBe('');
    });
  });

  describe('restore', () => {
    test('replaces current db with backup contents', () => {
      db.setFieldAt(10, 'k1', 'x', 'val1');
      const id = db.backup(10);
      db.setFieldAt(20, 'k2', 'y', 'val2'); // added after backup
      db.restore(30, id);
      expect(db.getFieldAt(30, 'k1', 'x')).toBe('val1');
      expect(db.getFieldAt(30, 'k2', 'y')).toBe('');
    });

    test('returns the count of keys restored as a string', () => {
      db.setFieldAt(10, 'k1', 'f', 'v');
      db.setFieldAt(10, 'k2', 'f', 'v');
      const id = db.backup(10);
      expect(db.restore(20, id)).toBe('2');
    });

    test('returns "" for non-existent backup ID', () => {
      expect(db.restore(10, 'backup_99')).toBe('');
    });

    test('recalculates TTLs after restore — remaining lifetime is preserved', () => {
      // set field at t=10 with TTL=100 → expiresAt=110
      db.setFieldWithTtl(10, 'k', 'f', 'v', 100);
      const id = db.backup(10); // backup at t=10; remaining TTL from t=10 = 100ms
      // restore at t=50: newExpiresAt = 50 + (110 - 10) = 150
      db.restore(50, id);
      expect(db.getFieldAt(149, 'k', 'f')).toBe('v');  // alive
      expect(db.getFieldAt(150, 'k', 'f')).toBe('');   // expired at 150
    });

    test('permanent fields remain permanent after restore', () => {
      db.setFieldAt(10, 'k', 'f', 'v');
      const id = db.backup(10);
      db.restore(999, id);
      expect(db.getFieldAt(9999999, 'k', 'f')).toBe('v');
    });
  });

  describe('compare', () => {
    test('returns "" when both backups are identical', () => {
      db.setFieldAt(10, 'k', 'f', 'v');
      const id1 = db.backup(10);
      const id2 = db.backup(10);
      expect(db.compare(id1, id2)).toBe('');
    });

    test('returns keys that exist in one backup but not the other', () => {
      db.setFieldAt(10, 'k1', 'f', 'v');
      const id1 = db.backup(10);
      db.setFieldAt(20, 'k2', 'g', 'w');
      const id2 = db.backup(20);
      // id1 has k1; id2 has k1 + k2 → k2 differs
      expect(db.compare(id1, id2)).toBe('k2');
    });

    test('returns keys with different field values', () => {
      db.setFieldAt(10, 'k', 'f', 'old');
      const id1 = db.backup(10);
      db.setFieldAt(20, 'k', 'f', 'new');
      const id2 = db.backup(20);
      expect(db.compare(id1, id2)).toBe('k');
    });

    test('returns "" for non-existent backup ID', () => {
      db.setFieldAt(10, 'k', 'f', 'v');
      const id1 = db.backup(10);
      expect(db.compare(id1, 'backup_99')).toBe('');
    });

    test('returns differing keys sorted alphabetically', () => {
      db.setFieldAt(10, 'z_key', 'f', 'v1');
      db.setFieldAt(10, 'a_key', 'f', 'v1');
      const id1 = db.backup(10);
      db.setFieldAt(20, 'z_key', 'f', 'v2');
      db.setFieldAt(20, 'a_key', 'f', 'v2');
      const id2 = db.backup(20);
      expect(db.compare(id1, id2)).toBe('a_key, z_key');
    });
  });

  describe('getBackupInfo', () => {
    test('returns keys, fields, and timestamp for a backup', () => {
      db.setFieldAt(10, 'k1', 'f1', 'v1');
      db.setFieldAt(10, 'k1', 'f2', 'v2');
      db.setFieldAt(10, 'k2', 'f1', 'v3');
      const id = db.backup(10);
      expect(db.getBackupInfo(id)).toBe('keys:2,fields:3,timestamp:10');
    });

    test('returns "" for non-existent backup ID', () => {
      expect(db.getBackupInfo('backup_99')).toBe('');
    });
  });
});
