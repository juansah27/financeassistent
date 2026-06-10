/**
 * Helper functions to format special command responses
 */

const formatRp = (value) => `Rp ${Number(value || 0).toLocaleString('id-ID', { maximumFractionDigits: 0 })}`;

const HELP_ALIASES = ['!help', 'help', 'bantuan', 'menu'];

const isHelpCommand = (text = '') => HELP_ALIASES.includes(text.toLowerCase().trim());

const getHelpMessage = () => (
    '🤖 *Menu Bantuan Bot Keuangan*\n\n' +
    'Ketik perintah atau catatan keuangan langsung di grup. Contoh yang bisa dipakai:\n\n' +
    '📝 *Catat transaksi*\n' +
    '• "beli nasi goreng 15k"\n' +
    '• "gajian 5jt"\n' +
    '• "bayar listrik 350rb"\n' +
    '• "transfer BCA ke GoPay 100rb"\n\n' +
    '💰 *Cek saldo & laporan*\n' +
    '• "cek saldo"\n' +
    '• "cek laporan" atau "laporan hari ini"\n' +
    '• "laporan mingguan"\n' +
    '• "analisa keuangan"\n' +
    '• "cek budget"\n\n' +
    '📅 *Tagihan, paylater, dan cicilan*\n' +
    '• "cek tagihan"\n' +
    '• "cek paylater"\n' +
    '• "gopaylater mie gacoan 60115 jatuh tempo 1 juli 2026"\n' +
    '• "netflix 65rb bulanan jatuh tempo tanggal 10"\n\n' +
    '🤝 *Hutang*\n' +
    '• "hutang" atau "cek hutang"\n' +
    '• "hutang minggu ini"\n' +
    '• "hutang telat"\n\n' +
    '🎯 *Tanya keuangan & target*\n' +
    '• "? berapa pengeluaran makan bulan ini"\n' +
    '• "? cek target keuangan"\n\n' +
    '📸 *Scan struk*\n' +
    '• Kirim foto struk, nanti bot bantu baca dan catat.\n\n' +
    'Tips: kalau salah catat, ikuti pertanyaan konfirmasi dari bot ya 👍'
);

const formatDebtResponse = (debts, type = 'all') => {
    if (!debts || debts.length === 0) {
        if (type === 'overdue') return '✅ Tidak ada hutang yang telat. Bagus!';
        if (type === 'week') return '✅ Tidak ada hutang yang jatuh tempo minggu ini.';
        return '✅ Tidak ada hutang aktif saat ini.';
    }

    let replyMessage = '';

    if (type === 'overdue') {
        const overdueDebts = debts.filter(d => d.is_overdue);
        if (overdueDebts.length === 0) return '✅ Tidak ada hutang yang telat. Bagus!';

        replyMessage = `🚨 *Hutang Telat*\n• Total: ${overdueDebts.length} tagihan\n\n`;
        overdueDebts.forEach((debt) => {
            const daysOverdue = Math.abs(debt.days_until_due || 0);
            replyMessage += `• ${debt.creditor || 'Tanpa nama'}\n  Sisa: ${formatRp(debt.remaining_amount)}\n  Status: telat ${daysOverdue} hari\n`;
        });
    }
    else if (type === 'week') {
        const weekDebts = debts.filter(d =>
            d.days_until_due !== null &&
            d.days_until_due >= 0 &&
            d.days_until_due <= 7
        );
        if (weekDebts.length === 0) return '✅ Tidak ada hutang yang jatuh tempo minggu ini.';

        replyMessage = `📅 *Hutang Jatuh Tempo Minggu Ini*\n• Total: ${weekDebts.length} tagihan\n\n`;
        weekDebts.forEach((debt) => {
            const daysText = debt.days_until_due === 0 ? 'hari ini' :
                debt.days_until_due === 1 ? 'besok' :
                    `${debt.days_until_due} hari lagi`;
            replyMessage += `• ${debt.creditor || 'Tanpa nama'}\n  Tagihan: ${formatRp(debt.installment_amount || debt.remaining_amount)}\n  Waktu: ${daysText}\n`;
        });
    }
    else {
        let totalRemaining = 0;
        replyMessage = `📋 *Daftar Hutang Aktif*\n• Total: ${debts.length} hutang\n\n`;
        debts.forEach((debt) => {
            totalRemaining += debt.remaining_amount || 0;
            const parts = [
                debt.creditor || 'Tanpa nama',
                `sisa ${formatRp(debt.remaining_amount)}`,
            ];
            if (debt.total_amount) parts.push(`total ${formatRp(debt.total_amount)}`);
            if (debt.tenor) parts.push(`cicilan ${debt.paid_count}/${debt.tenor}`);
            if (debt.next_payment_date && debt.days_until_due !== null) {
                const daysText = debt.is_overdue ? `telat ${Math.abs(debt.days_until_due)} hari` :
                    debt.days_until_due === 0 ? 'jatuh tempo hari ini' :
                        debt.days_until_due === 1 ? 'jatuh tempo besok' :
                            `jatuh tempo ${debt.days_until_due} hari lagi`;
                parts.push(daysText);
            }
            replyMessage += `• ${parts.join('\n  ')}\n`;
        });
        replyMessage += `\n💰 *Total sisa hutang: ${formatRp(totalRemaining)}*`;
    }

    return replyMessage.trim();
};

module.exports = {
    formatDebtResponse,
    getHelpMessage,
    isHelpCommand,
    HELP_ALIASES
};
