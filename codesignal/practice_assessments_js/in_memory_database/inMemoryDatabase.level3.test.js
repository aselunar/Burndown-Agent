const InMemoryDatabase = require('./inMemoryDatabase');

// LEVEL 3 — SET_FIELD_AT, SET_FIELD_WITH_TTL, GET_FIELD_AT, GET_AT,
//            DELETE_FIELD_AT, SCAN_AT, SCAN_BY_FIELD_AT
// KEY TRANSITIONS FROM L2:
//   • Field storage refactored: { value, expiresAt }  (expiresAt = null → no TTL)
//   • TTL unit: MILLISECONDS (FileStorage uses seconds — don't mix up!)
//   • Field valid [timestamp, timestamp+ttl); expired AT timestamp+ttl exactly
//   • All *_AT ops skip expired fields; SCAN_AT skips keys with ALL fields expired

describe('In-Memory Database — Level 3', () => {
  let db;

  beforeEach(() => {
    db = new InMemoryDatabase();
  });

  describe('setFieldAt / setFieldWithTtl', () => {
    test('setFieldAt sets a permanent field and returns value', () => {
      expect(db.setFieldAt(10, 'u', 'name', 'Alice')).toBe('Alice');
      expect(db.getFieldAt(999999, 'u', 'name')).toBe('Alice');
    });

    test('setFieldWithTtl sets a TTL field and returns value', () => {
      expect(db.setFieldWithTtl(10, 'u', 'token', 'abc123', 50)).toBe('abc123');
    });

    test('TTL field is available before expiry', () => {
      db.setFieldWithTtl(10, 'u', 'field', 'val', 20); // expires at t=30
      expect(db.getFieldAt(29, 'u', 'field')).toBe('val');
    });

    test('TTL field is expired AT expiresAt (unavailable at t=30 when expires=30)', () => {
      db.setFieldWithTtl(10, 'u', 'field', 'val', 20); // expiresAt = 10+20 = 30
      expect(db.getFieldAt(30, 'u', 'field')).toBe('');
    });
  });

  describe('getFieldAt', () => {
    test('returns "" for non-existent key', () => {
      expect(db.getFieldAt(10, 'ghost', 'f')).toBe('');
    });

    test('returns "" for an expired field', () => {
      db.setFieldWithTtl(5, 'u', 'x', 'v', 10); // expires at 15
      expect(db.getFieldAt(15, 'u', 'x')).toBe('');
    });
  });

  describe('getAt', () => {
    test('returns only non-expired fields sorted α', () => {
      db.setFieldWithTtl(10, 'u', 'name', 'Alice', 100); // expires at 110
      db.setFieldWithTtl(10, 'u', 'token', 'xyz', 5);   // expires at 15
      db.setFieldAt(10, 'u', 'city', 'LA');
      // at t=20: name and city alive, token expired
      expect(db.getAt(20, 'u')).toBe('city(LA), name(Alice)');
    });

    test('returns "" if key does not exist', () => {
      expect(db.getAt(10, 'ghost')).toBe('');
    });

    test('returns "" if all fields are expired', () => {
      db.setFieldWithTtl(10, 'u', 'x', 'v', 5); // expires at 15
      expect(db.getAt(15, 'u')).toBe('');
    });
  });

  describe('deleteFieldAt', () => {
    test('deletes a live field and returns "true"', () => {
      db.setFieldAt(10, 'u', 'f', 'v');
      expect(db.deleteFieldAt(20, 'u', 'f')).toBe('true');
    });

    test('returns "false" for an expired field', () => {
      db.setFieldWithTtl(10, 'u', 'f', 'v', 5); // expires at 15
      expect(db.deleteFieldAt(20, 'u', 'f')).toBe('false');
    });

    test('returns "false" for non-existent key or field', () => {
      expect(db.deleteFieldAt(10, 'ghost', 'f')).toBe('false');
    });
  });

  describe('scanAt', () => {
    test('returns keys with at least one alive field', () => {
      db.setFieldAt(10, 'user1', 'name', 'Alice');
      db.setFieldWithTtl(10, 'user2', 'token', 'xyz', 5); // expires at 15
      // at t=20: user2 is expired
      expect(db.scanAt(20, 'user')).toBe('user1');
    });

    test('returns "" when no alive keys match prefix', () => {
      db.setFieldWithTtl(10, 'user1', 'f', 'v', 1); // expires at 11
      expect(db.scanAt(20, 'user')).toBe('');
    });
  });

  describe('scanByFieldAt', () => {
    test('only includes keys where the field is alive with matching value', () => {
      db.setFieldAt(10, 'u1', 'role', 'admin');
      db.setFieldWithTtl(10, 'u2', 'role', 'admin', 5); // expires at 15
      expect(db.scanByFieldAt(20, 'role', 'admin')).toBe('u1');
    });
  });
});
