function formatRupiah(value) {
  const number = Number(value || 0);
  return `Rp ${number.toLocaleString('id-ID', { maximumFractionDigits: 0 })}`;
}

function extractLine(prefix, text) {
  if (!text) return null;
  const line = text
    .split(/\r?\n/)
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));
  return line || null;
}

function extractSection(marker, text) {
  if (!text) return null;
  const index = text.indexOf(marker);
  if (index === -1) return null;
  return text.slice(index).trim();
}

function formatMultiTransactionReply(results) {
  const successful = results.filter((item) => item.response && item.response.success);
  const failed = results.filter((item) => !item.response || !item.response.success);

  if (successful.length === 0) {
    return '⚠️ Belum ada transaksi yang berhasil dicatat dari pesan ini.';
  }

  const lines = successful.map((item, index) => {
    const response = item.response;
    const amount = formatRupiah(response.amount);
    const category = response.category || 'Lain-lain';
    const marker = response.type === 'INCOME' ? '📥' : '💸';
    return `• ${amount} | ${category} | ${item.line} ${marker}`;
  });

  const latestReply = successful[successful.length - 1].response.reply_message || '';
  const sisaBudget = extractLine('💰 Sisa Budget:', latestReply);
  const totalToday = extractLine('📊 Total Pengeluaran Hari Ini:', latestReply);
  const balanceSnapshot = extractSection('💳 *Sisa Saldo Terkait*', latestReply) || extractSection('💳 *Sisa Saldo*', latestReply) || extractSection('💳 Sisa Saldo', latestReply);

  let reply = `✅ *Berhasil dicatat*\n• Total: ${successful.length} transaksi\n\n${lines.join('\n')}`;

  if (failed.length > 0) {
    reply += `\n\n⚠️ Belum kebaca: ${failed.length} baris\n`;
    reply += failed.map((item) => `• ${item.line}`).join('\n');
  }

  if (sisaBudget || totalToday) {
    reply += '\n\n';
    if (sisaBudget) reply += `${sisaBudget}\n`;
    if (totalToday) reply += totalToday;
    reply = reply.trim();
  }

  if (balanceSnapshot) {
    reply += `\n\n${balanceSnapshot}`;
  }

  return reply;
}

module.exports = {
  formatMultiTransactionReply,
  formatRupiah,
};
