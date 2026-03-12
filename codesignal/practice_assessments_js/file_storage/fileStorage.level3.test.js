const FileStorage = require('./fileStorage');

// LEVEL 3 — FILE_UPLOAD_AT, FILE_GET_AT, FILE_COPY_AT, FILE_SEARCH_AT
// KEY TRANSITIONS FROM L2:
//   • Files now have optional TTL (in seconds).
//   • expiresAt = uploadedAt + ttl; file is EXPIRED at timestamp >= expiresAt
//   • All _AT variants ignore (exclude) expired files from results / operations
//   • TTL unit is SECONDS here — InMemoryDB uses milliseconds — don't mix them up!

describe('File Storage — Level 3', () => {
  let fs;

  beforeEach(() => {
    fs = new FileStorage();
  });

  describe('fileUploadAt', () => {
    test('uploads without TTL (lives forever)', () => {
      fs.fileUploadAt(10, 'forever.txt', 500);
      expect(fs.fileGetAt(999999, 'forever.txt')).toBe(500);
    });

    test('uploads with TTL; file expires at uploadedAt + ttl', () => {
      fs.fileUploadAt(10, 'temp.txt', 300, 20); // expires at t=30
      expect(fs.fileGetAt(29, 'temp.txt')).toBe(300); // alive
      expect(fs.fileGetAt(30, 'temp.txt')).toBeUndefined(); // expired AT 30
    });

    test('throws on duplicate file name', () => {
      fs.fileUploadAt(10, 'dupe.txt', 100);
      expect(() => fs.fileUploadAt(11, 'dupe.txt', 200)).toThrow();
    });
  });

  describe('fileGetAt', () => {
    test('returns size for a live file', () => {
      fs.fileUploadAt(10, 'file.txt', 123, 100);
      expect(fs.fileGetAt(50, 'file.txt')).toBe(123);
    });

    test('returns undefined for an expired file', () => {
      fs.fileUploadAt(10, 'file.txt', 123, 5); // expires at 15
      expect(fs.fileGetAt(15, 'file.txt')).toBeUndefined();
    });

    test('returns undefined for a non-existent file', () => {
      expect(fs.fileGetAt(10, 'ghost.txt')).toBeUndefined();
    });
  });

  describe('fileCopyAt', () => {
    test('copies a live file to a new destination', () => {
      fs.fileUploadAt(10, 'src.txt', 400, 100);
      fs.fileCopyAt(20, 'src.txt', 'dest.txt');
      expect(fs.fileGetAt(20, 'dest.txt')).toBe(400);
    });

    test('throws if source is expired at copy time', () => {
      fs.fileUploadAt(10, 'src.txt', 400, 5); // expires at 15
      expect(() => fs.fileCopyAt(20, 'src.txt', 'dest.txt')).toThrow();
    });

    test('overwrite destination if it already exists', () => {
      fs.fileUploadAt(10, 'src.txt', 800);
      fs.fileUploadAt(11, 'dest.txt', 100);
      // fileCopyAt throws on duplicate source name upload, not destination overwrite
      // need to manually remove dest first... actually fileCopyAt should overwrite
      // Here we test it directly by checking dest after copy
      fs.fileCopyAt(20, 'src.txt', 'dest.txt');
      expect(fs.fileGetAt(20, 'dest.txt')).toBe(800);
    });
  });

  describe('fileSearchAt', () => {
    test('excludes expired files from results', () => {
      fs.fileUploadAt(10, 'doc1.txt', 200, 10); // expires at 20
      fs.fileUploadAt(10, 'doc2.txt', 300, 100); // expires at 110
      const result = fs.fileSearchAt(25, 'doc');
      expect(result).toEqual(['doc2.txt(300)']);
    });

    test('includes files with no TTL', () => {
      fs.fileUploadAt(10, 'permanent.txt', 500);
      expect(fs.fileSearchAt(99999, 'perm')).toEqual(['permanent.txt(500)']);
    });

    test('returns top 10 alive files sorted size DESC then name ASC', () => {
      fs.fileUploadAt(1, 'z.txt', 100, 500);
      fs.fileUploadAt(2, 'a.txt', 100, 500);
      const result = fs.fileSearchAt(10, '');
      expect(result[0]).toBe('a.txt(100)'); // tie in size → alphabetical
      expect(result[1]).toBe('z.txt(100)');
    });
  });
});
