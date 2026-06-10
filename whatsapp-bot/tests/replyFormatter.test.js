const assert = require('assert');
const { formatMultiTransactionReply } = require('../utils/replyFormatter');

function run() {
  const reply = formatMultiTransactionReply([
    {
      line: 'beli risol 1000',
      response: {
        success: true,
        transaction_id: 101,
        amount: 1000,
        category: 'Konsumsi',
        type: 'EXPENSE',
        reply_message: '✅ Sudah Tercatat :\n\n- 08:00 | Rp 1.000 | beli risol 1000 | Juansah | Konsumsi\n\n💰 Sisa Budget: Rp 900.000\n📊 Total Pengeluaran Hari Ini: Rp 10.000'
      }
    },
    {
      line: 'beli ketan 2500',
      response: {
        success: true,
        transaction_id: 102,
        amount: 2500,
        category: 'Lain-lain',
        type: 'EXPENSE',
        reply_message: '✅ Sudah Tercatat :\n\n- 08:01 | Rp 2.500 | beli ketan 2500 | Juansah | Lain-lain\n\n💰 Sisa Budget: Rp 897.500\n📊 Total Pengeluaran Hari Ini: Rp 12.500'
      }
    }
  ]);

  assert(reply.includes('✅ Sudah Tercatat:'));
  assert(reply.includes('2 transaksi'));
  assert(reply.includes('1. Rp 1.000 | Konsumsi | beli risol 1000'));
  assert(reply.includes('2. Rp 2.500 | Lain-lain | beli ketan 2500'));
  assert(reply.includes('💰 Sisa Budget: Rp 897.500'));
  assert(reply.includes('📊 Total Pengeluaran Hari Ini: Rp 12.500'));
}

run();
console.log('replyFormatter tests passed');
