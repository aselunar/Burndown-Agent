const BankingSystem = require('./bankingSystem');

// LEVEL 3 — SCHEDULE_PAYMENT, ACCEPT_PAYMENT, TOP_ACTIVITY
// KEY TRANSITIONS FROM L2:
//   • withdraw/transfer now return payment_id (not balance) when amount > 1000
//   • call _processScheduled at top of every mutating operation
//
// TRICKY:
//   • Scheduled payments fire BEFORE the current operation if executeAt <= timestamp
//   • payment_id format: "payment_1", "payment_2", ... (sequential, never reset)
//   • acceptPayment re-checks balance at time of acceptance (not at scheduling time)

describe('Banking System — Level 3', () => {
  let bank;

  beforeEach(() => {
    bank = new BankingSystem();
    bank.createAccount(1, 'alice');
    bank.createAccount(2, 'bob');
    bank.deposit(3, 'alice', 5000);
    bank.deposit(4, 'bob', 2000);
  });

  describe('withdraw / transfer — large amount guard', () => {
    test('withdraw > 1000 returns payment_id instead of balance', () => {
      const result = bank.withdraw(10, 'alice', 1500);
      expect(result).toBe('payment_1');
    });

    test('withdraw <= 1000 still works normally', () => {
      expect(bank.withdraw(10, 'alice', 999)).toBe('4001');
    });

    test('transfer > 1000 returns payment_id', () => {
      const result = bank.transfer(10, 'alice', 'bob', 2000);
      expect(result).toBe('payment_1');
    });

    test('each large transaction gets a unique sequential payment_id', () => {
      const id1 = bank.withdraw(10, 'alice', 1500);
      const id2 = bank.transfer(11, 'alice', 'bob', 1200);
      expect(id1).toBe('payment_1');
      expect(id2).toBe('payment_2');
    });

    test('withdraw > 1000 with insufficient funds still returns ""', () => {
      bank.createAccount(5, 'poor');
      bank.deposit(6, 'poor', 100);
      expect(bank.withdraw(10, 'poor', 1500)).toBe('');
    });
  });

  describe('acceptPayment', () => {
    test('completes a pending withdrawal and returns new balance', () => {
      const refId = bank.withdraw(10, 'alice', 1500);
      expect(bank.acceptPayment(20, 'alice', refId)).toBe('3500');
    });

    test('completes a pending transfer and returns source balance', () => {
      const refId = bank.transfer(10, 'alice', 'bob', 2000);
      expect(bank.acceptPayment(20, 'alice', refId)).toBe('3000');
    });

    test('returns "" for non-existent reference', () => {
      expect(bank.acceptPayment(10, 'alice', 'payment_99')).toBe('');
    });

    test('returns "" if same reference accepted twice (already processed)', () => {
      const refId = bank.withdraw(10, 'alice', 1500);
      bank.acceptPayment(20, 'alice', refId);
      expect(bank.acceptPayment(30, 'alice', refId)).toBe('');
    });

    test('balance is NOT deducted until acceptPayment is called', () => {
      bank.withdraw(10, 'alice', 1500); // pending, not yet deducted
      expect(bank.deposit(11, 'alice', 0)).toBe('5000'); // still 5000
    });
  });

  describe('schedulePayment', () => {
    test('returns "true" when successfully scheduled', () => {
      expect(bank.schedulePayment(10, 'alice', 200, 'DEPOSIT', 50)).toBe('true');
    });

    test('returns "" for non-existent account', () => {
      expect(bank.schedulePayment(10, 'ghost', 200, 'DEPOSIT', 50)).toBe('');
    });

    test('scheduled deposit fires at executeAt and changes balance', () => {
      bank.schedulePayment(10, 'alice', 500, 'DEPOSIT', 100); // fires at t=110
      // trigger at t=110 or later
      expect(bank.deposit(110, 'alice', 0)).toBe('5500');
    });

    test('scheduled withdraw fires and reduces balance', () => {
      bank.schedulePayment(10, 'alice', 300, 'WITHDRAW', 50); // fires at t=60
      expect(bank.deposit(100, 'alice', 0)).toBe('4700');
    });

    test('scheduled payment does NOT fire before executeAt', () => {
      bank.schedulePayment(10, 'alice', 500, 'DEPOSIT', 100); // fires at t=110
      expect(bank.deposit(50, 'alice', 0)).toBe('5000'); // t=50 < 110
    });

    test('multiple scheduled payments fire in chronological order', () => {
      bank.schedulePayment(10, 'alice', 100, 'DEPOSIT', 20); // fires at t=30
      bank.schedulePayment(10, 'alice', 200, 'DEPOSIT', 10); // fires at t=20
      // At t=50 both should have fired: 5000 + 200 + 100 = 5300
      expect(bank.deposit(50, 'alice', 0)).toBe('5300');
    });
  });

  describe('topActivity', () => {
    test('counts history + scheduled + pending for each account', () => {
      // beforeEach: alice has deposit(3,5000)=1 history, bob has deposit(4,2000)=1 history
      bank.deposit(10, 'alice', 100);       // alice now has 2 history entries
      bank.withdraw(11, 'alice', 200);      // alice now has 3 (withdraw ≤1000 completes immediately)
      bank.schedulePayment(12, 'bob', 100, 'DEPOSIT', 1000); // bob: 1 history + 1 scheduled = 2
      const result = bank.topActivity(20, 2);
      expect(result).toBe('alice(3), bob(2)');
    });

    test('tie-breaks alphabetically', () => {
      // beforeEach: alice has 1 history, bob has 1 history
      bank.deposit(10, 'alice', 50);  // alice: 2 history
      bank.deposit(11, 'bob', 50);    // bob:   2 history — tied; alice < bob alphabetically
      const result = bank.topActivity(20, 2);
      expect(result).toBe('alice(2), bob(2)');
    });
  });
});
