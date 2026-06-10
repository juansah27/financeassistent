const { downloadMediaMessage } = require('@whiskeysockets/baileys');
const fs = require('fs');
const path = require('path');
const mime = require('mime-types');
const ApiService = require('../services/api');
const { TEMP_DIR } = require('../config');

// Ensure temp dir exists
if (!fs.existsSync(TEMP_DIR)) {
    fs.mkdirSync(TEMP_DIR, { recursive: true });
}

/**
 * Process image message for OCR
 */
const processImageMessage = async (sock, msg, groupName, senderName) => {
    let tempFilePath = null;
    try {
        const remoteJid = msg.key.remoteJid;

        console.log('⬇️ Downloading image...');
        const buffer = await downloadMediaMessage(
            msg,
            'buffer',
            {},
            {
                logger: console,
                reuploadRequest: sock.updateMediaMessage
            }
        );

        if (!buffer) {
            console.error('Failed to download media');
            return;
        }

        // Determine extension
        const imageMessage = msg.message.imageMessage;
        const mimetype = imageMessage.mimetype || 'image/jpeg';
        const ext = mime.extension(mimetype) || 'jpg';

        // Save to temp file
        const filename = `ocr_${Date.now()}_${msg.key.id}.${ext}`;
        tempFilePath = path.join(TEMP_DIR, filename);
        fs.writeFileSync(tempFilePath, buffer);

        console.log(`💾 Saved to ${tempFilePath}`);

        // Notify user
        // await sock.sendMessage(remoteJid, { text: '⏳ Memproses gambar...' }, { quoted: msg });

        const metadata = {
            sender: senderName,
            sender_number: (msg.key.participant || msg.key.remoteJid).replace('@s.whatsapp.net', ''),
            group_name: groupName,
            group_id: remoteJid,
            timestamp: new Date((msg.messageTimestamp || Date.now() / 1000) * 1000).toISOString(),
            message_id: msg.key.id
        };

        // Send to API
        const response = await ApiService.sendImageToOCR(tempFilePath, filename, metadata);

        // Process response
        if (response && response.success) {
            let replyText = response.reply_message;
            if (!replyText) {
                const amount = Number(response.amount || 0).toLocaleString('id-ID', { maximumFractionDigits: 0 });
                replyText = `✅ *Struk berhasil dibaca*\n• Nominal: Rp ${amount}\n• Kategori: ${response.category || 'Lain-lain'}`;
            }
            await sock.sendMessage(remoteJid, { text: replyText }, { quoted: msg });
        } else {
            const errorMessage = response?.user_message || '❌ Gagal membaca gambar.';
            await sock.sendMessage(remoteJid, { text: errorMessage }, { quoted: msg });
        }

    } catch (error) {
        console.error('Error processing image:', error);
        await sock.sendMessage(msg.key.remoteJid, { text: '❌ Terjadi kesalahan saat memproses gambar.' }, { quoted: msg });
    } finally {
        // Cleanup
        if (tempFilePath && fs.existsSync(tempFilePath)) {
            try {
                fs.unlinkSync(tempFilePath);
            } catch (e) {
                console.error('Failed to cleanup temp file:', e);
            }
        }
    }
};

module.exports = { processImageMessage };
