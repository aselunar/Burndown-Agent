const BankingSystem = require('./bankingSystem');

// LEVEL 1 — CREATE_ACCOUNT, DEPOSIT, WITHDRAW, TRANSFER
// Key returns: "true"/"false" (strings!), balance as string, "" on error

describe('Banking System — Level 1', () => {
  let bank;

  beforeEach(() => {
    bank = new BankingSystem();
  });

  describe('createAccount', () => {
    test('creates a new account and returns "true"', () => {
      expect(bank.createAccount(1, 'acc1')).toBe('true');
    });

    test('returns "false" when account already exists', () => {
      bank.createAccount(1, 'acc1');
      expect(bank.createAccount(2, 'acc1')).toBe('false');
    });

    test('creates multiple distinct accounts', () => {
      expect(bank.createAccount(1, 'acc1')).toBe('true');
      expect(bank.createAccount(2, 'acc2')).toBe('true');
    });
  });

  describe('deposit', () => {
    test('returns new balance as string after deposit', () => {
      bank.createAccount(1, 'acc1');
      expect(bank.deposit(2, 'acc1', 500)).toBe('500');
    });

    test('returns "" for non-existent account', () => {
      expect(bank.deposit(1, 'ghost', 100)).toBe('');
    });

    test('accumulates multiple deposits', () => {
      bank.createAccount(1, 'acc1');
      bank.deposit(2, 'acc1', 200);
      expect(bank.deposit(3, 'acc1', 300)).toBe('500');
    });
  });

  describe('withdraw', () => {
    test('returns new balance after successful withdrawal', () => {
      bank.createAccount(1, 'acc1');
      bank.deposit(2, 'acc1', 1000);
      expect(bank.withdraw(3, 'acc1', 400)).toBe('600');
    });

    test('returns "" when account does not exist', () => {
      expect(bank.withdraw(1, 'ghost', 100)).toBe('');
    });

    test('returns "" on insufficient funds (balance < amount)', () => {
      bank.createAccount(1, 'acc1');
      bank.deposit(2, 'acc1', 100);
      expect(bank.withdraw(3, 'acc1', 200)).toBe('');
    });

    test('allows withdrawing exact balance', () => {
      bank.createAccount(1, 'acc1');
      bank.deposit(2, 'acc1', 500);
      expect(bank.withdraw(3, 'acc1', 500)).toBe('0');
    });
  });

  describe('transfer', () => {
    test('transfers funds and returns source balance', () => {
      bank.createAccount(1, 'acc1');
      bank.createAccount(2, 'acc2');
      bank.deposit(3, 'acc1', 1000);
      expect(bank.transfer(4, 'acc1', 'acc2', 300)).toBe('700');
    });

    test('returns "" when source does not exist', () => {
      bank.createAccount(1, 'acc2');
      expect(bank.transfer(2, 'ghost', 'acc2', 100)).toBe('');
    });

    test('returns "" when target does not exist', () => {
      bank.createAccount(1, 'acc1');
      bank.deposit(2, 'acc1', 500);
      expect(bank.transfer(3, 'acc1', 'ghost', 100)).toBe('');
    });

    test('returns "" on insufficient funds in source', () => {
      bank.createAccount(1, 'acc1');
      bank.createAccount(2, 'acc2');
      bank.deposit(3, 'acc1', 50);
      expect(bank.transfer(4, 'acc1', 'acc2', 100)).toBe('');
    });

    test('target account receives the transferred amount', () => {
      bank.createAccount(1, 'acc1');
      bank.createAccount(2, 'acc2');
      bank.deposit(3, 'acc1', 1000);
      bank.transfer(4, 'acc1', 'acc2', 400);
      expect(bank.deposit(5, 'acc2', 0)).toBe('400');
    });
  });
});
