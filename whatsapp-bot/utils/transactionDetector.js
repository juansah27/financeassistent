/**
 * Transaction Intent Detection & Error Handling
 * 
 * Detects if a message is a transaction command with confidence levels:
 * - HIGH: Transaction keyword + amount → Process
 * - MEDIUM: Transaction keyword exists but incomplete → Ask clarification
 * - LOW: Normal conversation → Ignore
 */

// Transaction keywords by category
const TRANSACTION_KEYWORDS = {
    expense: ['beli', 'belanja', 'bayar', 'jajan', 'topup', 'isi', 'langganan', 'makan', 'minum', 'donasi', 'traktir', 'sumbangan', 'sedekah', 'ngasih', 'kasih'],
    debtCreation: ['hutang', 'pinjem', 'minjem'],
    debtPayment: ['bayar', 'cicil', 'nyicil', 'lunasin'],
    income: ['gaji', 'bonus', 'terima', 'masuk'],
    transfer: ['transfer', 'kirim uang', 'pindah saldo']
};

// All transaction keywords combined
const ALL_TRANSACTION_KEYWORDS = [
    ...TRANSACTION_KEYWORDS.expense,
    ...TRANSACTION_KEYWORDS.debtCreation,
    ...TRANSACTION_KEYWORDS.income,
    ...TRANSACTION_KEYWORDS.transfer
];

// Amount patterns (Indonesian format)
const AMOUNT_PATTERNS = [
    /\d+[.,]?\d*\s*(?:rb|ribu|k|jt|juta|m)/i,  // 50k, 50rb, 50ribu, 5jt, 5juta
    /rp\s*\d+[.,]?\d*/i,                         // Rp 50.000
    /\d{1,3}(?:[.,]\d{3})+/                       // 50.000 or 50,000
];

// Confusion words - look like transactions but are conversation
const CONFUSION_PATTERNS = [
    /beli\s+(?:apa|sih|yang|mana|gimana|dong|aja|dulu|nanti|ya|deh)/i,
    /bayar\s+(?:apa|sih|yang|mana|gimana|dong|aja|dulu|nanti|ya|deh|itu|ini)/i,
    /hutang\s+(?:apa|sih|yang|mana|gimana|dong|aja|dulu|nanti|ya|deh|itu|ini|adalah|merupakan)/i,
    /transfer\s+(?:apa|sih|yang|mana|gimana|dong|aja|dulu|nanti|ya|deh)/i,
    /lagi\s+(?:beli|bayar|hutang|transfer|jajan)/i,
    /mau\s+(?:beli|bayar|hutang|transfer|jajan)/i,
    /akan\s+(?:beli|bayar|hutang|transfer|jajan)/i,
    /sedang\s+(?:beli|bayar|hutang|transfer|jajan)/i,
    /terima\s+(?:kasih|dong|aja|sih)/i,
    /gaji\s+(?:berapa|kapan|udah|sudah|belum|nya)/i,
    /gajian\s+(?:kapan|udah|sudah|belum|berapa)/i,
    /kapan\s+(?:gaji|gajian|bayar|hutang)/i
];

/**
 * Detect transaction intent with confidence level
 * @param {string} text - Message text
 * @returns {Object} { confidence: 'high'|'medium'|'low'|'none', type: string|null, hasAmount: boolean }
 */
function detectTransactionIntent(text) {
    const lowerText = text.toLowerCase().trim();
    
    // Check if it's a confusion pattern (conversation about transactions)
    const isConfusion = CONFUSION_PATTERNS.some(pattern => pattern.test(lowerText));
    if (isConfusion) {
        return { confidence: 'none', type: null, hasAmount: false, reason: 'conversation' };
    }
    
    // Check for transaction keywords
    let detectedKeyword = null;
    let detectedType = null;
    
    for (const [type, keywords] of Object.entries(TRANSACTION_KEYWORDS)) {
        for (const keyword of keywords) {
            if (lowerText.includes(keyword)) {
                detectedKeyword = keyword;
                detectedType = type;
                break;
            }
        }
        if (detectedKeyword) break;
    }
    
    if (!detectedKeyword) {
        return { confidence: 'none', type: null, hasAmount: false, reason: 'no_keyword' };
    }
    
    // Check for amount
    const hasAmount = AMOUNT_PATTERNS.some(pattern => pattern.test(text));
    
    // Determine confidence level
    if (hasAmount) {
        // HIGH: Has both keyword and amount
        return { confidence: 'high', type: detectedType, hasAmount: true };
    } else {
        // MEDIUM: Has keyword but no amount
        return { confidence: 'medium', type: detectedType, hasAmount: false };
    }
}

/**
 * Check if message is a normal conversation (not a transaction)
 * @param {string} text - Message text
 * @returns {boolean}
 */
function isNormalConversation(text) {
    const intent = detectTransactionIntent(text);
    return intent.confidence === 'none' || intent.confidence === 'low';
}

/**
 * Generate user-friendly error message
 * @param {string} errorType - Error type
 * @param {Object} context - Error context
 * @returns {string} WhatsApp-formatted error message
 */
function getErrorMessage(errorType, context = {}) {
    const messages = {
        'unknown_command': `❌ Perintah tidak dikenali

Contoh:
• bunda hutang 100k dari lia
• lia hutang 100k ke bunda
• bunda bayar 50k ke lia`,

        'missing_amount': `❌ Nominal tidak ditemukan

Contoh:
• bunda bayar 50k ke lia
• beli bubur 30k`,

        'person_not_found': `❌ Nama "${context.name || ''}" tidak ditemukan

Pastikan nama sudah terdaftar.`,

        'account_not_found': `❌ Akun "${context.name || ''}" tidak ditemukan

Akun tersedia: dompet, atm bca, gopay, shopeepay`,

        'insufficient_balance': `❌ Saldo tidak mencukupi

💳 ${context.accountName || 'Akun'}: Rp ${(context.balance || 0).toLocaleString('id-ID')}
💸 Transaksi: Rp ${(context.amount || 0).toLocaleString('id-ID')}`,

        'debt_not_found': `❌ Tidak ditemukan hutang aktif

Cek daftar hutang: ? hutang`,

        'overpayment': `❌ Jumlah bayar melebihi sisa hutang

Sisa hutang: Rp ${(context.remaining || 0).toLocaleString('id-ID')}
Jumlah bayar: Rp ${(context.amount || 0).toLocaleString('id-ID')}`,

        'internal_error': `❌ Terjadi kesalahan saat memproses transaksi

Silakan coba lagi beberapa saat.`,

        'clarification_needed': `🤔 Data transaksi belum lengkap

Contoh:
• bunda bayar 50k ke lia
• beli bubur 30k
• transfer 100k ke bca`,

        'both_external': `❌ Maaf, hutang antara orang luar belum didukung

Hanya bisa mencatat:
• Hutang dari/ke anggota keluarga`,

        'payment_both_external': `❌ Maaf, pembayaran antara orang luar belum didukung

Hanya bisa mencatat:
• Pembayaran dari/ke anggota keluarga`
    };
    
    return messages[errorType] || messages['internal_error'];
}

/**
 * Validate transaction data and return friendly errors
 * @param {Object} data - Transaction data
 * @param {string} messageType - 'expense'|'income'|'transfer'|'debt_creation'|'debt_payment'
 * @returns {Object} { valid: boolean, error: string|null }
 */
function validateTransaction(data, messageType) {
    // Check for amount
    if (!data.amount || data.amount <= 0) {
        return { valid: false, error: getErrorMessage('missing_amount') };
    }
    
    // Check for person (if required)
    if (messageType.includes('debt') && !data.person && !data.target) {
        return { valid: false, error: getErrorMessage('unknown_command') };
    }
    
    return { valid: true, error: null };
}

module.exports = {
    detectTransactionIntent,
    isNormalConversation,
    getErrorMessage,
    validateTransaction,
    TRANSACTION_KEYWORDS,
    ALL_TRANSACTION_KEYWORDS,
    AMOUNT_PATTERNS
};
