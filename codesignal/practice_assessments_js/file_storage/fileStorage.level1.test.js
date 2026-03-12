const FileStorage = require('./fileStorage');

// LEVEL 1 — FILE_UPLOAD, FILE_GET, FILE_COPY
// KEY: upload THROWS on duplicate (does NOT return "false" or "")
//      fileCopy THROWS if source missing; overwrites silently if dest exists

describe('File Storage — Level 1', () => {
  let fs;

  beforeEach(() => {
    fs = new FileStorage();
  });

  describe('fileUpload', () => {
    test('uploads a file without error', () => {
      expect(() => fs.fileUpload('file.txt', 100)).not.toThrow();
    });

    test('throws when uploading a duplicate file name', () => {
      fs.fileUpload('file.txt', 100);
      expect(() => fs.fileUpload('file.txt', 200)).toThrow();
    });

    test('allows uploading different file names', () => {
      expect(() => fs.fileUpload('a.txt', 10)).not.toThrow();
      expect(() => fs.fileUpload('b.txt', 20)).not.toThrow();
    });
  });

  describe('fileGet', () => {
    test('returns file size after upload', () => {
      fs.fileUpload('file.txt', 1234);
      expect(fs.fileGet('file.txt')).toBe(1234);
    });

    test('returns undefined for a non-existent file', () => {
      expect(fs.fileGet('ghost.txt')).toBeUndefined();
    });
  });

  describe('fileCopy', () => {
    test('copies a file to a new destination', () => {
      fs.fileUpload('original.txt', 500);
      fs.fileCopy('original.txt', 'copy.txt');
      expect(fs.fileGet('copy.txt')).toBe(500);
    });

    test('throws if source file does not exist', () => {
      expect(() => fs.fileCopy('ghost.txt', 'dest.txt')).toThrow();
    });

    test('overwrites destination if it already exists', () => {
      fs.fileUpload('src.txt', 300);
      fs.fileUpload('dest.txt', 100);
      fs.fileCopy('src.txt', 'dest.txt');
      expect(fs.fileGet('dest.txt')).toBe(300);
    });
  });
});
