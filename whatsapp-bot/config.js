require('dotenv').config();

const path = require('path');

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_URL = process.env.API_URL || 'http://web:8000';
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || 'your-webhook-secret-change-this';

// Allowed groups (comma-separated group names or IDs, empty = all groups)
const CONFIGURED_ALLOWED_GROUPS = process.env.ALLOWED_GROUPS ?
    process.env.ALLOWED_GROUPS.split(',').map(g => g.trim()).filter(Boolean) :
    [];

// Stable group IDs that are known finance groups. Keeping IDs here lets the bot
// keep working when Baileys cannot fetch groupMetadata after a fresh QR login.
const DEFAULT_ALLOWED_GROUP_IDS = [
    '120363398239342501@g.us', // Happy Family 🥰
];

const ALLOWED_GROUPS = [...new Set([...CONFIGURED_ALLOWED_GROUPS, ...DEFAULT_ALLOWED_GROUP_IDS])];

// If both configured and default allow-lists are empty, allow all groups
const ALLOW_ALL_GROUPS = ALLOWED_GROUPS.length === 0;

// Message prefix (optional, empty = no prefix required)
const MESSAGE_PREFIX = process.env.MESSAGE_PREFIX || '';

module.exports = {
    API_URL,
    WEBHOOK_SECRET,
    ALLOWED_GROUPS,
    ALLOW_ALL_GROUPS,
    MESSAGE_PREFIX,
    // Paths
    AUTH_DIR: path.join(__dirname, 'auth_info'),
    TEMP_DIR: path.join(__dirname, 'temp')
};
