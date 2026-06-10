const assert = require('assert');
const path = require('path');

const apiPath = path.resolve(__dirname, '../services/api.js');
const configPath = path.resolve(__dirname, '../config.js');
const commandPath = path.resolve(__dirname, '../handlers/command.js');
const imagePath = path.resolve(__dirname, '../handlers/image.js');
let webhookCalls = [];

require.cache[configPath] = {
  id: configPath,
  filename: configPath,
  loaded: true,
  exports: {
    ALLOWED_GROUPS: [],
    ALLOW_ALL_GROUPS: true,
    MESSAGE_PREFIX: '',
  },
};

require.cache[commandPath] = {
  id: commandPath,
  filename: commandPath,
  loaded: true,
  exports: {
    formatDebtResponse: () => '',
  },
};

require.cache[imagePath] = {
  id: imagePath,
  filename: imagePath,
  loaded: true,
  exports: {
    processImageMessage: async () => {},
  },
};

require.cache[apiPath] = {
  id: apiPath,
  filename: apiPath,
  loaded: true,
  exports: {
    sendToWebhook: async (payload) => {
      webhookCalls.push(payload);
      const amount = payload.message.includes('ketan') ? 2500 : 1000;
      return {
        success: true,
        transaction_id: webhookCalls.length,
        amount,
        category: payload.message.includes('ketan') ? 'Lain-lain' : 'Konsumsi',
        type: 'EXPENSE',
        reply_message: `✅ Sudah Tercatat :\n\n- 08:0${webhookCalls.length} | Rp ${amount} | ${payload.message} | Juansah | Test\n\n💰 Sisa Budget: Rp 900.000\n📊 Total Pengeluaran Hari Ini: Rp 12.500`,
      };
    },
    getDebts: async () => [],
    askQuestion: async () => 'ok',
  },
};

const { handleMessage } = require('../handlers/message');

async function run() {
  const sentMessages = [];
  const sock = {
    groupMetadata: async () => ({ subject: 'Finance Test Group' }),
    sendMessage: async (jid, content, options) => {
      sentMessages.push({ jid, content, options });
    },
  };

  const msg = {
    key: {
      remoteJid: '12345@g.us',
      participant: '6281111111111@s.whatsapp.net',
      id: 'TEST-MULTILINE-1',
    },
    pushName: 'Juansah',
    messageTimestamp: Math.floor(Date.now() / 1000),
    message: {
      conversation: 'beli risol 1000\nbeli ketan 2500',
    },
  };

  await handleMessage(sock, msg);

  assert.strictEqual(webhookCalls.length, 2, 'should call webhook once per transaction line');
  assert.strictEqual(sentMessages.length, 1, 'should send only one aggregated WhatsApp reply');
  assert(sentMessages[0].content.text.includes('2 transaksi'));
  assert(sentMessages[0].content.text.includes('beli risol 1000'));
  assert(sentMessages[0].content.text.includes('beli ketan 2500'));
}

run().then(() => console.log('message handler multi-line test passed'));
