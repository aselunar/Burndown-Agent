const InMemoryDatabase = require('./inMemoryDatabase');

// LEVEL 1 — SET_FIELD, GET_FIELD, DELETE_FIELD, GET
// KEY: keys are auto-created on setField; auto-deleted when last field removed
// GET output: "field(val), field(val)" sorted ALPHABETICALLY by field name

describe('In-Memory Database — Level 1', () => {
  let db;

  beforeEach(() => {
    db = new InMemoryDatabase();
  });

  describe('setField', () => {
    test('sets a field and returns the value', () => {
      expect(db.setField('user1', 'name', 'Alice')).toBe('Alice');
    });

    test('overwrites an existing field value', () => {
      db.setField('user1', 'name', 'Alice');
      db.setField('user1', 'name', 'Bob');
      expect(db.getField('user1', 'name')).toBe('Bob');
    });

    test('creates the key automatically if it does not exist', () => {
      db.setField('newkey', 'field', 'val');
      expect(db.getField('newkey', 'field')).toBe('val');
    });
  });

  describe('getField', () => {
    test('returns the field value', () => {
      db.setField('u', 'age', '30');
      expect(db.getField('u', 'age')).toBe('30');
    });

    test('returns "" when key does not exist', () => {
      expect(db.getField('ghost', 'any')).toBe('');
    });

    test('returns "" when field does not exist on key', () => {
      db.setField('u', 'name', 'X');
      expect(db.getField('u', 'missing')).toBe('');
    });
  });

  describe('deleteField', () => {
    test('deletes an existing field and returns "true"', () => {
      db.setField('u', 'f', 'v');
      expect(db.deleteField('u', 'f')).toBe('true');
    });

    test('returns "false" when key does not exist', () => {
      expect(db.deleteField('ghost', 'f')).toBe('false');
    });

    test('returns "false" when field does not exist', () => {
      db.setField('u', 'other', 'v');
      expect(db.deleteField('u', 'missing')).toBe('false');
    });

    test('removes the key entirely when last field is deleted', () => {
      db.setField('u', 'only', 'v');
      db.deleteField('u', 'only');
      expect(db.getField('u', 'only')).toBe('');
    });
  });

  describe('get', () => {
    test('returns all fields sorted alphabetically', () => {
      db.setField('u', 'city', 'NYC');
      db.setField('u', 'age', '30');
      db.setField('u', 'name', 'Alice');
      expect(db.get('u')).toBe('age(30), city(NYC), name(Alice)');
    });

    test('returns "" for non-existent key', () => {
      expect(db.get('ghost')).toBe('');
    });

    test('returns single field correctly', () => {
      db.setField('u', 'x', 'y');
      expect(db.get('u')).toBe('x(y)');
    });
  });
});
