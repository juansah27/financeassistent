const { ALLOWED_GROUPS, ALLOW_ALL_GROUPS, MESSAGE_PREFIX } = require('../config');
const ApiService = require('../services/api');
const { formatDebtResponse, getHelpMessage, isHelpCommand } = require('./command');
const { processImageMessage } = require('./image');
const { formatMultiTransactionReply } = require('../utils/replyFormatter');

/**
 * Check if group is allowed
 */
const isGroupAllowed = (groupParams) => {
    // groupParams can be name or id
    const { name, id } = groupParams;

    if (ALLOW_ALL_GROUPS) return true;

    // Check if ID matches
    const idMatch = ALLOWED_GROUPS.some(allowed => id && id.includes(allowed));
    if (idMatch) return true;

    // Check if Name matches partial
    if (name) {
        return ALLOWED_GROUPS.some(allowed => name.toLowerCase().includes(allowed.toLowerCase()));
    }

    return false;
};

/**
 * Handle incoming messages
 */
const handleMessage = async (sock, msg) => {
    try {
        if (!msg.message) {
            console.log(`ℹ️ Ignoring message without content: ${msg.key?.id || 'unknown'}`);
            return;
        }

        // Extract message data
        const key = msg.key;
        const remoteJid = key.remoteJid;
        const isGroup = remoteJid.endsWith('@g.us');
        const sender = key.participant || key.remoteJid;
        const pushName = msg.pushName || 'Unknown';

        // 1. FILTER: Ignore non-group messages
        if (!isGroup) {
            // console.log('Ignoring private message');
            return;
        }

        // Get Group Metadata (to check name)
        // Note: In high traffic, we might want to cache this or assume ALLOWED_GROUPS contains IDs
        let groupName = 'Unknown Group';
        try {
            const groupMetadata = await Promise.race([
                sock.groupMetadata(remoteJid),
                new Promise(resolve => setTimeout(() => resolve(null), 3000)),
            ]);
            if (groupMetadata?.subject) {
                groupName = groupMetadata.subject;
            } else {
                console.log(`⚠️ groupMetadata timeout/empty for ${remoteJid}; falling back to group ID allow-list`);
            }
        } catch (e) {
            console.log(`⚠️ Failed to get group metadata for ${remoteJid}: ${e.message}`);
        }

        // Determine message content type
        const messageContent = msg.message;
        const textMessage = messageContent.conversation ||
            messageContent.extendedTextMessage?.text ||
            messageContent.ephemeralMessage?.message?.conversation ||
            messageContent.ephemeralMessage?.message?.extendedTextMessage?.text ||
            messageContent.viewOnceMessage?.message?.conversation ||
            messageContent.viewOnceMessage?.message?.extendedTextMessage?.text ||
            '';
        const imageMessage = messageContent.imageMessage ||
            messageContent.ephemeralMessage?.message?.imageMessage ||
            messageContent.viewOnceMessage?.message?.imageMessage;
        const messageTypes = Object.keys(messageContent || {}).join(',') || 'none';
        console.log(`🧭 Handler accepted ${remoteJid} (${groupName}) from ${pushName}; types=${messageTypes}; text="${textMessage.substring(0, 40)}"`);

        // 1.5 DEBUG: Check Group ID command (Bypasses allowed filter)
        if (textMessage.toLowerCase() === '!checkgroup') {
            const infoMsg = `📋 *Group Info*\nName: ${groupName}\nID: ${remoteJid}`;
            console.log(`Sending group info to ${groupName} (${remoteJid})`);
            await sock.sendMessage(remoteJid, { text: infoMsg }, { quoted: msg });
            return;
        }

        // 2. FILTER: Check Allowed Groups
        if (!isGroupAllowed({ name: groupName, id: remoteJid })) {
            // Log only unique ignore messages to prevent spamming logs
            console.log(`🚫 Ignoring message from unauthorized group: "${groupName}" (${remoteJid})`);
            return;
        }

        // 3. ROUTE: Image Handling (OCR)
        if (imageMessage) {
            console.log(`📷 Image detected from ${pushName} in ${groupName}`);
            await processImageMessage(sock, msg, groupName, pushName);
            return;
        }

        if (!textMessage) {
            console.log(`ℹ️ Ignoring unsupported message type from ${groupName} (${remoteJid}); types=${messageTypes}`);
            return;
        }

        const lowerText = textMessage.toLowerCase().trim();

        // 3.1 ROUTE: Help menu (read-only, do not forward to webhook/transaction parser)
        if (isHelpCommand(textMessage)) {
            await sock.sendMessage(remoteJid, { text: getHelpMessage() }, { quoted: msg });
            return;
        }

        // 3.5 ROUTE: Recurring / Paylater Commands (Direct API)
        if (lowerText === 'cek paylater' || lowerText.startsWith('cek paylater ') || lowerText === 'list paylater' || lowerText === 'daftar paylater') {
            const recurring = await ApiService.getRecurringList('paylater');
            const reply = recurring.reply_message || '🔄 *Daftar Paylater*\n• Belum ada data yang cocok';
            await sock.sendMessage(remoteJid, { text: reply }, { quoted: msg });
            return;
        }

        if ([
            'cek tagihan', 'cek tagihan aktif', 'list tagihan', 'daftar tagihan',
            'cek recurring', 'cek recurring aktif', 'list recurring', 'daftar recurring'
        ].includes(lowerText)) {
            const recurring = await ApiService.getRecurringList('');
            const reply = recurring.reply_message || '🔄 *Daftar Tagihan*\n• Belum ada tagihan yang cocok';
            await sock.sendMessage(remoteJid, { text: reply }, { quoted: msg });
            return;
        }

        // 3.6 ROUTE: Financial Q&A (Starts with '?' or 'tanya')
        // Strict check: Must start with '?'
        if (lowerText.startsWith('?') || lowerText.startsWith('tanya ')) {
            let question = '';

            if (lowerText.startsWith('?')) {
                question = textMessage.substring(1).trim();
            } else {
                question = textMessage.substring(6).trim(); // Remove "tanya "
            }

            // Send "Trying..." presence (optional, maybe just log)
            console.log(`🤔 Q&A Request from ${pushName}: ${question}`);

            // Call API
            const answerHTML = await ApiService.askQuestion(question);

            // Check if response is already plain text (no HTML tags) or contains HTML
            const hasHTMLTags = /<[^>]+>/.test(answerHTML);

            let answerWA;

            if (!hasHTMLTags) {
                // Response is already plain text with newlines, use as-is
                answerWA = answerHTML.trim();
            } else {
                // Convert HTML answer to WhatsApp Format (Refined)
                answerWA = answerHTML
                    // 1. Remove literal newlines from source (HTML ignores them, rely on tags)
                    .replace(/\r?\n/g, '')

                    // 2. Handle block elements
                    .replace(/<br\s*\/?>/gi, '\n')
                    .replace(/<\/p>/gi, '\n\n')
                    .replace(/<ul.*?>/gi, '\n')
                    .replace(/<\/ul>/gi, '') // No extra newline at end of ul
                    .replace(/<li.*?>/gi, '• ')
                    .replace(/<\/li>/gi, '\n')

                    // 3. Formatting
                    .replace(/<strong>(.*?)<\/strong>/gi, '*$1*')
                    .replace(/<b>(.*?)<\/b>/gi, '*$1*')

                    // 4. Cleanup
                    .replace(/<span.*?>(.*?)<\/span>/gi, '$1')
                    .replace(/<[^>]+>/g, '') // Strip remaining tags
                    .replace(/&nbsp;/g, ' ')

                    // 5. Post-processing
                    .replace(/\n\s*\n\s*\n+/g, '\n\n') // Max 2 newlines
                    .trim();
            }

            // Send Reply
            await sock.sendMessage(remoteJid, { text: answerWA }, { quoted: msg });
            return;
        }

        // 4. ROUTE: Debt Commands (Direct API)
        if (['hutang', 'tagihan', 'my debt'].includes(lowerText)) {
            const debts = await ApiService.getDebts();
            const reply = formatDebtResponse(debts, 'all');
            await sock.sendMessage(remoteJid, { text: reply }, { quoted: msg });
            return;
        }
        if (lowerText === 'hutang telat') {
            const debts = await ApiService.getDebts();
            const reply = formatDebtResponse(debts, 'overdue');
            await sock.sendMessage(remoteJid, { text: reply }, { quoted: msg });
            return;
        }
        if (lowerText === 'hutang minggu ini') {
            const debts = await ApiService.getDebts();
            const reply = formatDebtResponse(debts, 'week');
            await sock.sendMessage(remoteJid, { text: reply }, { quoted: msg });
            return;
        }

        // 5. ROUTE: General Transaction / Report (Webhook)
        // Basic filter: must contain numbers or keywords
        // Simple logic similar to old bot: length > 4 and (hasNumbers OR isReportCommand)
        const isReportCommand = [
            "share report", "share dashboard", "laporan hari ini", "cek laporan", "info keuangan",
            "cek budgeting", "info budget", "status budget", "sisa budget", "cek budget",
            "analisa pengeluaran", "analisa keuangan", "analisis pengeluaran",
            "pengeluaran minggu lalu", "laporan mingguan", "cek minggu lalu",
            "agar bisa kaya", "advice keuangan", "saran keuangan", "apa yang harus saya lakukan",
            "cek sisa saldo", "cek saldo", "sisa saldo", "total saldo", "saldo keluarga", "cek balance",
            "cek hutang", "daftar hutang", "info hutang",
            "bantuan", "help", "perintah", "command", "menu"
        ].some(cmd => lowerText.includes(cmd));
        const hasNumbers = /\d/.test(textMessage);

        // Check if message is a potential confirmation reply (short, no numbers)
        const isConfirmation = ["ya", "yes", "y", "ok", "tidak", "no", "n", "batal"].includes(lowerText);

        if (textMessage.length < 2) return; // Allow length 2 ("no"/"ya")

        if (!hasNumbers && !isReportCommand && !isConfirmation) {
            // Likely chat, ignore
            console.log(`ℹ️ Ignoring non-transaction message: "${textMessage.substring(0, 20)}..."`);
            return;
        }

        console.log(`📨 Processing message from ${pushName} in "${groupName}" (${remoteJid}): "${textMessage.substring(0, 50)}..."`);

        // Prepare payload
        const timestamp = new Date((msg.messageTimestamp || Date.now() / 1000) * 1000).toISOString();

        // Split multi-line messages into individual transactions
        const lines = textMessage.split('\n').map(l => l.trim()).filter(l => l.length > 0);

        const webhookResults = [];

        // Process each line as a separate transaction, but aggregate replies for multi-line input
        for (const line of lines) {
            if (isHelpCommand(line)) {
                await sock.sendMessage(remoteJid, { text: getHelpMessage() }, { quoted: msg });
                continue;
            }

            const lineHasNumbers = /\d/.test(line);
            const lineIsReport = [
                "share report", "share dashboard", "laporan hari ini", "cek laporan", "info keuangan",
                "cek budgeting", "info budget", "status budget", "sisa budget", "cek budget",
                "analisa pengeluaran", "analisa keuangan", "analisis pengeluaran",
                "pengeluaran minggu lalu", "laporan mingguan", "cek minggu lalu",
                "agar bisa kaya", "advice keuangan", "saran keuangan", "apa yang harus saya lakukan",
            "cek sisa saldo", "cek saldo", "sisa saldo", "total saldo", "saldo keluarga", "cek balance",
            "cek hutang", "daftar hutang", "info hutang",
            "bantuan", "help", "perintah", "command", "menu"
            ].some(cmd => line.toLowerCase().includes(cmd));
            if (lines.length > 1 && !lineHasNumbers && !lineIsReport) {
                console.log(`⏭️ Skipping non-transaction line in multi-line: "${line.substring(0, 30)}"`);
                continue;
            }

            const payload = {
                message: line,
                sender: pushName,
                sender_number: sender.replace('@s.whatsapp.net', ''),
                group_name: groupName,
                group_id: remoteJid,
                timestamp: timestamp,
                message_id: key.id
            };

            // Call webhook to backend
            const response = await ApiService.sendToWebhook(payload);
            webhookResults.push({ line, response });

            // 6. REPLY HANDLING for single-line input: preserve existing behavior
            if (lines.length === 1) {
                if (response && response.success) {
                    let replyText = response.reply_message;
                    console.log(`✅ Webhook success: ID ${response.transaction_id || 'N/A'}`);

                    // Fallback formatting if generic success
                    if (!replyText && response.transaction_id) {
                        replyText = `✓ Transaksi ID: ${response.transaction_id}\nJumlah: ${response.amount}\nKategori: ${response.category}`;
                    }

                    if (replyText) {
                        console.log(`📤 Sending reply to ${remoteJid}`);
                        await sock.sendMessage(remoteJid, { text: replyText }, { quoted: msg });
                        console.log(`✅ Reply sent!`);
                    } else {
                        console.log(`⚠️ No reply text generated from backend response.`);
                    }
                } else {
                    console.log(`⚠️ Webhook returned error or no success flag:`, response);
                }
            }
        }

        if (lines.length > 1 && webhookResults.length > 0) {
            const replyText = formatMultiTransactionReply(webhookResults);
            console.log(`📤 Sending aggregated multi-transaction reply to ${remoteJid}`);
            await sock.sendMessage(remoteJid, { text: replyText }, { quoted: msg });
            console.log(`✅ Aggregated reply sent!`);
        }

    } catch (err) {
        console.error('Error handling message:', err);
    }
};

module.exports = { handleMessage };

