const BankingSystem = require('./bankingSystem');

// LEVEL 4 — MERGE_ACCOUNTS, GET_BANK_STATISTICS, CASHBACK
// KEY TRANSITIONS FROM L3:
//   • mergeAccounts must re-point ALL state for acc2 → acc1
//     (balance, history, outgoing, scheduled, pending)
//   • getBankStatistics uses Math.floor for average
//   • cashback applies % to total outgoing (WITHDRAW + TRANSFER_OUT only)

describe('Banking System — Level 4', () => {
  let bank;

  beforeEach(() => {
    bank = new BankingSystem();
    bank.createAccount(1, 'alice');
    bank.createAccount(2, 'bob');
    bank.deposit(3, 'alice', 2000);
    bank.deposit(4, 'bob', 1000);
  });

  describe('mergeAccounts', () => {
    test('adds bob balance into alice and deletes bob', () => {
      expect(bank.mergeAccounts(10, 'alice', 'bob')).toBe('3000');
    });

    test('bob no longer exists after merge', () => {
      bank.mergeAccounts(10, 'alice', 'bob');
      expect(bank.deposit(11, 'bob', 100)).toBe(''); // "" — does not exist
    });

    test('alice retains merged bob history', () => {
      bank.withdraw(5, 'bob', 100); // bob history
      bank.mergeAccounts(10, 'alice', 'bob');
      // alice should now have bob's WITHDRAW in history (n=10 to get all)
      const hist = bank.getPaymentHistory(20, 'alice', 10);
      expect(hist).toContain('WITHDRAW(100)');
    });

    test('returns "" when either account does not exist', () => {
      expect(bank.mergeAccounts(10, 'alice', 'ghost')).toBe('');
      expect(bank.mergeAccounts(10, 'ghost', 'alice')).toBe('');
    });

    test('merged outgoing totals are combined', () => {
      bank.withdraw(5, 'alice', 200);
      bank.withdraw(6, 'bob', 100);
      bank.mergeAccounts(10, 'alice', 'bob');
      expect(bank.topSpenders(20, 1)).toBe('alice(300)');
    });

    test('pending payment originally for bob is transferred to alice', () => {
      bank.deposit(5, 'bob', 5000); // ensure sufficient balance
      const refId = bank.withdraw(6, 'bob', 1500); // creates pending for bob
      bank.mergeAccounts(10, 'alice', 'bob');
      // Now accepting should work against alice's account
      const result = bank.acceptPayment(20, 'alice', refId);
      expect(result).not.toBe('');
    });
  });

  describe('getBankStatistics', () => {
    test('returns correct totals for all active accounts', () => {
      // alice=2000, bob=1000 → total=3000, count=2, avg=1500
      expect(bank.getBankStatistics(10)).toBe(
        'total_accounts:2,total_balance:3000,average_balance:1500'
      );
    });

    test('average is floored (not rounded)', () => {
      bank.createAccount(5, 'carol');
      bank.deposit(6, 'carol', 1); // alice=2000, bob=1000, carol=1 → total=3001, avg=floor(3001/3)=1000
      expect(bank.getBankStatistics(10)).toBe(
        'total_accounts:3,total_balance:3001,average_balance:1000'
      );
    });

    test('deleted accounts are not included in statistics', () => {
      bank.mergeAccounts(10, 'alice', 'bob'); // bob deleted
      expect(bank.getBankStatistics(20)).toBe(
        'total_accounts:1,total_balance:3000,average_balance:3000'
      );
    });
  });

  describe('cashback', () => {
    test('returns cashback amount deposited (floor of pct * outgoing)', () => {
      bank.withdraw(5, 'alice', 500);
      // 5% of 500 = 25
      expect(bank.cashback(10, 'alice', 5)).toBe('25');
    });

    test('cashback increases account balance', () => {
      bank.withdraw(5, 'alice', 500); // alice now has 1500
      bank.cashback(10, 'alice', 10); // 10% of 500 = 50
      expect(bank.deposit(11, 'alice', 0)).toBe('1550');
    });

    test('returns "" for non-existent account', () => {
      expect(bank.cashback(10, 'ghost', 5)).toBe('');
    });

    test('returns "" when account has no spending', () => {
      expect(bank.cashback(10, 'alice', 5)).toBe('');
    });

    test('floors the cashback amount', () => {
      bank.withdraw(5, 'alice', 99); // 3% of 99 = 2.97 → floor = 2
      expect(bank.cashback(10, 'alice', 3)).toBe('2');
    });

    test('includes transfer_out in cashback calculation', () => {
      bank.createAccount(5, 'carol');
      bank.transfer(6, 'alice', 'carol', 400);
      // 10% of 400 = 40
      expect(bank.cashback(10, 'alice', 10)).toBe('40');
    });
  });
});
