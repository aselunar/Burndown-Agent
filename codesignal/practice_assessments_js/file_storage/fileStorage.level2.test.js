const FileStorage = require('./fileStorage');

// LEVEL 2 — FILE_SEARCH
// Returns top 10 files with the given prefix.
// Sort: size DESC (primary), fileName ASC (secondary — NOT size ASC)
// Returns array of "name(size)" strings.

describe('File Storage — Level 2', () => {
  let fs;

  beforeEach(() => {
    fs = new FileStorage();
  });

  describe('fileSearch', () => {
    test('returns files matching the prefix', () => {
      fs.fileUpload('doc.txt', 100);
      fs.fileUpload('doc_notes.txt', 200);
      fs.fileUpload('image.png', 300);
      expect(fs.fileSearch('doc')).toEqual(['doc_notes.txt(200)', 'doc.txt(100)']);
    });

    test('sorts by size DESC', () => {
      fs.fileUpload('a.txt', 50);
      fs.fileUpload('b.txt', 200);
      fs.fileUpload('c.txt', 100);
      const result = fs.fileSearch('');
      expect(result[0]).toBe('b.txt(200)');
      expect(result[1]).toBe('c.txt(100)');
      expect(result[2]).toBe('a.txt(50)');
    });

    test('tie-breaks by file name ASC when sizes are equal', () => {
      fs.fileUpload('z_file.txt', 500);
      fs.fileUpload('a_file.txt', 500);
      const result = fs.fileSearch('');
      // a_file < z_file alphabetically
      expect(result[0]).toBe('a_file.txt(500)');
      expect(result[1]).toBe('z_file.txt(500)');
    });

    test('returns at most 10 results', () => {
      for (let i = 1; i <= 15; i++) {
        fs.fileUpload(`file${i}.txt`, i * 10);
      }
      expect(fs.fileSearch('file').length).toBe(10);
    });

    test('returns empty array when no files match prefix', () => {
      fs.fileUpload('document.txt', 100);
      expect(fs.fileSearch('xyz')).toEqual([]);
    });

    test('prefix "" matches all files', () => {
      fs.fileUpload('any.txt', 1);
      expect(fs.fileSearch('').length).toBe(1);
    });
  });
});
