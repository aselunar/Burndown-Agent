const BankingSystem = require('./bankingSystem');

// LEVEL 2 — TOP_SPENDERS, GET_PAYMENT_HISTORY
// Tricky: outgoing only counts WITHDRAW + TRANSFER_OUT (not DEPOSIT or TRANSFER_IN)
// Sort: primary = outgoing DESC, secondary = accountId ASC (lexicographic tie-break)
// History: most recent FIRST; TRANSFER uses TRANSFER_IN / TRANSFER_OUT labels

describe('Banking System — Level 2', () => {
  let bank;

  beforeEach(() => {
    bank = new BankingSystem();
    bank.createAccount(1, 'alice');
    bank.createAccount(2, 'bob');
    bank.createAccount(3, 'carol');
    bank.deposit(4, 'alice', 2000);
    bank.deposit(5, 'bob', 1500);
    bank.deposit(6, 'carol', 1000);
  });

  describe('topSpenders', () => {
    test('returns top spenders sorted by outgoing DESC', () => {
      bank.withdraw(10, 'alice', 500);
      bank.withdraw(11, 'bob', 300);
      expect(bank.topSpenders(20, 2)).toBe('alice(500), bob(300)');
    });

    test('includes transfer_out in outgoing but not deposits', () => {
      bank.transfer(10, 'alice', 'bob', 400);
      bank.deposit(11, 'alice', 100); // deposit does NOT count as outgoing
      expect(bank.topSpenders(20, 3)).toBe('alice(400)');
    });

    test('tie-breaks alphabetically when outgoing amounts are equal', () => {
      bank.withdraw(10, 'alice', 200);
      bank.withdraw(11, 'bob', 200);
      // alice < bob alphabetically → alice listed first
      expect(bank.topSpenders(20, 2)).toBe('alice(200), bob(200)');
    });

    test('returns fewer than n when not enough spenders', () => {
      bank.withdraw(10, 'alice', 100);
      expect(bank.topSpenders(20, 5)).toBe('alice(100)');
    });

    test('returns "" when no one has spent', () => {
      expect(bank.topSpenders(20, 3)).toBe('');
    });
  });

  describe('getPaymentHistory', () => {
    test('returns most recent operations first', () => {
      bank.deposit(10, 'alice', 100);
      bank.withdraw(11, 'alice', 50);
      // withdraw comes last → appears first in history
      expect(bank.getPaymentHistory(20, 'alice', 2)).toBe('WITHDRAW(50), DEPOSIT(100)');
    });

    test('labels transfer operations correctly', () => {
      bank.transfer(10, 'alice', 'bob', 300);
      expect(bank.getPaymentHistory(20, 'alice', 1)).toBe('TRANSFER_OUT(300)');
      expect(bank.getPaymentHistory(20, 'bob', 1)).toBe('TRANSFER_IN(300)');
    });

    test('returns "" for non-existent account', () => {
      expect(bank.getPaymentHistory(10, 'ghost', 5)).toBe('');
    });

    test('returns all history when n > history length', () => {
      // beforeEach deposited 2000 for alice already; add one more
      bank.deposit(10, 'alice', 100);
      // n=100 returns ALL entries, most recent first
      expect(bank.getPaymentHistory(20, 'alice', 100)).toBe('DEPOSIT(100), DEPOSIT(2000)');
    });

    test('limits to n most recent', () => {
      bank.deposit(10, 'alice', 100);
      bank.deposit(11, 'alice', 200);
      bank.deposit(12, 'alice', 300);
      // n=2 → last two (300, 200), most recent first
      expect(bank.getPaymentHistory(20, 'alice', 2)).toBe('DEPOSIT(300), DEPOSIT(200)');
    });

    test('returns "" for an account that exists but has no history', () => {
      bank.createAccount(100, 'dave');
      expect(bank.getPaymentHistory(200, 'dave', 5)).toBe('');
    });
  });
});
