const InMemoryDatabase = require('./inMemoryDatabase');

// LEVEL 2 — SCAN, SCAN_BY_FIELD, DELETE, TOP_N_KEYS
// KEY TRANSITIONS FROM L1:
//   • SCAN: prefix match on keys, sort α, return ", "-joined string (not array)
//   • TOP_N_KEYS: count DESC, key ASC tie-break
//   • DELETE: removes entire key (vs deleteField which removes one field)
// TRICKY: scan/scanByField return "" (empty string) when nothing matches

describe('In-Memory Database — Level 2', () => {
  let db;

  beforeEach(() => {
    db = new InMemoryDatabase();
    db.setField('user1', 'name', 'Alice');
    db.setField('user1', 'age', '30');
    db.setField('user2', 'name', 'Bob');
    db.setField('admin1', 'role', 'superadmin');
  });

  describe('scan', () => {
    test('returns all keys matching the prefix, sorted', () => {
      expect(db.scan('user')).toBe('user1, user2');
    });

    test('returns "" when no keys match', () => {
      expect(db.scan('xyz')).toBe('');
    });

    test('prefix "" matches all keys', () => {
      const result = db.scan('');
      expect(result).toContain('user1');
      expect(result).toContain('user2');
      expect(result).toContain('admin1');
    });
  });

  describe('scanByField', () => {
    test('returns keys where field=value, sorted alphabetically', () => {
      db.setField('user3', 'name', 'Alice');
      expect(db.scanByField('name', 'Alice')).toBe('user1, user3');
    });

    test('returns "" when no keys match', () => {
      expect(db.scanByField('name', 'Nobody')).toBe('');
    });

    test('is exact value match (not prefix)', () => {
      expect(db.scanByField('name', 'Al')).toBe('');
    });
  });

  describe('delete', () => {
    test('removes the entire key and all its fields', () => {
      expect(db.delete('user1')).toBe('true');
      expect(db.getField('user1', 'name')).toBe('');
    });

    test('returns "false" when key does not exist', () => {
      expect(db.delete('ghost')).toBe('false');
    });

    test('key no longer appears in scan after deletion', () => {
      db.delete('user1');
      expect(db.scan('user')).toBe('user2');
    });
  });

  describe('topNKeys', () => {
    test('returns top n keys by field count, most fields first', () => {
      // user1 has 2 fields, user2 has 1, admin1 has 1
      expect(db.topNKeys(1)).toBe('user1(2)');
    });

    test('tie-breaks alphabetically when counts are equal', () => {
      // user2 and admin1 both have 1 field; admin1 < user2 alphabetically
      expect(db.topNKeys(3)).toBe('user1(2), admin1(1), user2(1)');
    });

    test('returns all keys when n > total key count', () => {
      const result = db.topNKeys(100);
      expect(result.split(', ').length).toBe(3);
    });

    test('returns "" when database is empty', () => {
      const emptyDb = new InMemoryDatabase();
      expect(emptyDb.topNKeys(5)).toBe('');
    });
  });
});
