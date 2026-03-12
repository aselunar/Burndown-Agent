const FileStorage = require('./fileStorage');

// LEVEL 4 — ROLLBACK
// KEY TRANSITIONS FROM L3:
//   • Snapshots taken after every _AT operation
//   • rollback(ts) restores to the LATEST snapshot with snapshot.timestamp <= ts
//   • TTL recalc formula: newExpiresAt = rollbackCallTimestamp + (oldExpiresAt - snapshotTimestamp)
//     This preserves remaining lifetime as of the snapshot moment.
//   • Files already expired at the snapshot time are NOT included in the restore

describe('File Storage — Level 4', () => {
  let fs;

  beforeEach(() => {
    fs = new FileStorage();
  });

  describe('rollback', () => {
    test('restores files to the state at a given timestamp', () => {
      fs.fileUploadAt(10, 'file1.txt', 100); // snapshot at t=10
      fs.fileUploadAt(20, 'file2.txt', 200); // snapshot at t=20
      fs.rollback(10);
      // After rollback to t=10: only file1 should exist
      expect(fs.fileGetAt(10, 'file1.txt')).toBe(100);
      expect(fs.fileGetAt(10, 'file2.txt')).toBeUndefined();
    });

    test('recalculates TTL after rollback', () => {
      // upload at t=10 with TTL=50 → expires at t=60
      // snapshot at t=10 captures this file
      fs.fileUploadAt(10, 'temp.txt', 500, 50);
      // rollback called at t=30 targeting t=10 snapshot
      // remaining TTL at snapshot = 60 - 10 = 50
      // new expiresAt = 30 + 50 = 80
      fs.rollback(30);
      expect(fs.fileGetAt(79, 'temp.txt')).toBe(500); // alive
      expect(fs.fileGetAt(80, 'temp.txt')).toBeUndefined(); // expired at 80
    });

    test('files with no TTL remain alive after rollback', () => {
      fs.fileUploadAt(10, 'forever.txt', 300);
      fs.rollback(50);
      expect(fs.fileGetAt(999999, 'forever.txt')).toBe(300);
    });

    test('files that were already expired at snapshot time are excluded after rollback', () => {
      // upload at t=5 with TTL=3 → expires at t=8
      // file expired by t=10 (the snapshot time)
      fs.fileUploadAt(5, 'short.txt', 100, 3); // expires at 8
      fs.fileUploadAt(10, 'anchor.txt', 200);   // this creates the snapshot at t=10
      fs.rollback(10);
      expect(fs.fileGetAt(10, 'short.txt')).toBeUndefined(); // was expired at snapshot time
    });

    test('rollback with no matching snapshot does nothing', () => {
      fs.fileUploadAt(100, 'late.txt', 999);
      // rollback to t=5 — no snapshot exists before t=100
      fs.rollback(5);
      // late.txt should still exist (rollback had no effect)
      expect(fs.fileGetAt(100, 'late.txt')).toBe(999);
    });

    test('subsequent operations after rollback work correctly', () => {
      fs.fileUploadAt(10, 'file1.txt', 100);
      fs.fileUploadAt(20, 'file2.txt', 200);
      fs.rollback(10);
      // Can upload file2 again after rollback since it no longer exists
      expect(() => fs.fileUploadAt(30, 'file2.txt', 999)).not.toThrow();
      expect(fs.fileGetAt(30, 'file2.txt')).toBe(999);
    });
  });
});
