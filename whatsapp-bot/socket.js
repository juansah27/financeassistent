const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');
const fs = require('fs/promises'); // Add fs for folder deletion
const { AUTH_DIR } = require('./config');
const { handleMessage } = require('./handlers/message');

// Simple cache for message deduplication
const processedMessages = new Set();

// Track messages sent by this bot process so their fromMe echoes are ignored,
// while manual messages typed from the linked WhatsApp account can still be processed.
const botSentMessageIds = new Set();

function trackSentMessage(result, context = '') {
    const id = result?.key?.id;
    if (id) {
        botSentMessageIds.add(id);
        console.log(`🧾 Tracking bot-sent message${context ? ` (${context})` : ''}: ${id}`);
    }
    return result;
}

// Clean up processed/sent message caches every 1 hour to prevent memory leaks
setInterval(() => {
    processedMessages.clear();
    botSentMessageIds.clear();
}, 3600 * 1000);

// Global socket instance
let sock;
let connectionState = 'disconnected';
let currentQR = null;
let isIntentionalLogout = false;

async function sendMessage(jid, content, options = {}) {
    if (!sock || connectionState !== 'connected') {
        throw new Error(`WhatsApp client not connected (status=${connectionState})`);
    }
    const result = await sock.sendMessage(jid, content, options);
    return trackSentMessage(result, 'api/sendMessage');
}

// Get current status
function getStatus() {
    return {
        status: connectionState,
        qr: currentQR
    };
}

// Logout / Reset Session
async function logout() {
    try {
        console.log('🚪 Initiating secure logout...');
        isIntentionalLogout = true;

        if (sock) {
            // First close socket
            try {
                await sock.logout();
            } catch (e) {
                console.log('Socket logout error (ignoring):', e.message);
                sock.end(undefined);
            }
        }

        // Reset state
        connectionState = 'disconnected';
        currentQR = null;
        sock = null;

        // Force delete auth directory
        console.log(`🗑️ Deleting auth directory: ${AUTH_DIR}`);
        try {
            await fs.rm(AUTH_DIR, { recursive: true, force: true });
            console.log('✅ Auth directory deleted.');
        } catch (e) {
            console.error('Failed to delete auth dir:', e);
        }

        // Restart connection process (will generate new QR)
        setTimeout(() => {
            isIntentionalLogout = false;
            connectToWhatsApp();
        }, 1000);

        return true;
    } catch (error) {
        console.error('Logout error:', error);
    }
    return false;
}

async function connectToWhatsApp() {
    // Ensure dir exists (or handled by baileys)

    let state, saveCreds;
    try {
        const authData = await useMultiFileAuthState(AUTH_DIR);
        state = authData.state;
        saveCreds = authData.saveCreds;
    } catch (e) {
        console.error('Auth state init error:', e);
        return;
    }

    // Fetch latest version
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`Using WA v${version.join('.')}, isLatest: ${isLatest}`);

    sock = makeWASocket({
        version,
        logger: pino({ level: 'silent' }),
        auth: state,
        // Standard browser config to avoid 405/401 loops
        browser: ['Ubuntu', 'Chrome', '20.0.04']
    });

    // Track every message this Node process sends (handler replies, API sends, alerts)
    // so its WhatsApp echo can be ignored without ignoring manual fromMe group commands.
    const originalSendMessage = sock.sendMessage.bind(sock);
    sock.sendMessage = async (...args) => {
        const result = await originalSendMessage(...args);
        return trackSentMessage(result, 'sock.sendMessage');
    };

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            connectionState = 'scanning';
            currentQR = qr;
            console.log('QR Code received, scan with WhatsApp:');
            qrcode.generate(qr, { small: true });
            // Save QR as PNG image
            QRCode.toFile('/app/auth_info/qr.png', qr, { width: 400 }, (err) => {
                if (err) console.error('Failed to save QR image:', err);
                else console.log('📸 QR image saved to /app/auth_info/qr.png');
            });
        }

        if (connection === 'close') {
            connectionState = 'disconnected';
            currentQR = null;

            if (isIntentionalLogout) {
                console.log('🔒 Intentional logout completed. Not reconnecting via update loop.');
                return;
            }

            const statusCode = (lastDisconnect?.error instanceof Boom)
                ? lastDisconnect.error.output?.statusCode
                : null;

            const isLoggedOut = statusCode === DisconnectReason.loggedOut;
            const is401 = statusCode === 401;

            console.log('❌ Connection closed due to ', lastDisconnect?.error, '| statusCode:', statusCode);

            if (isLoggedOut || is401) {
                // Session was revoked by WhatsApp (e.g. after reset/logout on phone)
                // Must clear auth files so a fresh QR code can be generated
                console.log('🗑️ Session revoked (401/loggedOut). Clearing auth files for fresh QR...');
                try {
                    await fs.rm(AUTH_DIR, { recursive: true, force: true });
                    console.log('✅ Auth files cleared. Will reconnect and show QR.');
                } catch (e) {
                    console.error('Failed to clear auth dir:', e);
                }
                setTimeout(connectToWhatsApp, 2000);
            } else {
                // Normal disconnect — just reconnect with existing session
                setTimeout(connectToWhatsApp, 2000);
            }
        } else if (connection === 'open') {
            connectionState = 'connected';
            currentQR = null;
            isIntentionalLogout = false;
            console.log('✅ Baileys Client is ready!');
            console.log('-----------------------------');

            // Sync groups
            console.log('🔄 Fetching groups...');
            try {
                const groups = await sock.groupFetchAllParticipating();
                const groupList = Object.values(groups).map(g => ({
                    id: g.id,
                    subject: g.subject
                }));

                console.log(`Found ${groupList.length} groups. Syncing to backend...`);
                // Import dynamically to avoid circular dependency
                const ApiService = require('./services/api');
                ApiService.syncGroups(groupList).catch(err => console.error("Sync failed:", err));
            } catch (err) {
                console.error('Failed to sync groups:', err);
            }
        }
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        console.log(`📥 Event: messages.upsert | Type: ${type} | Count: ${messages.length}`);

        // Log the raw message structure for the first message (to debug)
        if (messages.length > 0) {
            // Safe stringify to avoid circular ref issues if any (though unlikely for raw msg)
            try {
                console.log('Raw Msg Key:', JSON.stringify(messages[0].key));
            } catch (e) { console.log('Could not log raw msg key'); }
        }

        if (type === 'notify' || type === 'append') { // Expanded types just in case
            for (const msg of messages) {
                const messageId = msg.key.id;
                const remoteJid = msg.key.remoteJid || '';
                const isGroupManualCommand = msg.key.fromMe && remoteJid.endsWith('@g.us') && type === 'notify';

                if (processedMessages.has(messageId)) {
                    console.log(`⚠️ Skipping duplicate message ID: ${messageId}`);
                    continue;
                }

                if (msg.key.fromMe && botSentMessageIds.has(messageId)) {
                    processedMessages.add(messageId);
                    console.log(`Ignoring bot-sent echo: ${messageId}`);
                    continue;
                }

                if (msg.key.fromMe && !isGroupManualCommand) {
                    console.log(`Ignoring fromMe sync/private/history message: ${messageId}`);
                    continue;
                }

                processedMessages.add(messageId);
                console.log(`▶️ Passing message ${messageId} to handler${msg.key.fromMe ? ' (fromMe manual group command)' : ''}...`);
                await handleMessage(sock, msg);
            }
        }
    });
}

async function getGroupMetadata(groupId) {
    if (!sock) {
        throw new Error('WhatsApp client not connected');
    }
    return await sock.groupMetadata(groupId);
}

module.exports = { connectToWhatsApp, sendMessage, getStatus, logout, getGroupMetadata };
