const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const { API_URL, WEBHOOK_SECRET } = require('../config');

// Create axios instance with default config
const apiClient = axios.create({
    baseURL: API_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
        'X-Webhook-Secret': WEBHOOK_SECRET
    },
    responseType: 'json'
});

const ApiService = {
    /**
     * Send message to backend webhook for classification and processing
     */
    async sendToWebhook(data) {
        try {
            console.log(`🌐 Sending to webhook: ${API_URL}/api/whatsapp/webhook`);
            const response = await apiClient.post('/api/whatsapp/webhook', data);
            return response.data;
        } catch (error) {
            console.error('❌ Error sending to webhook:', error.message);
            if (error.response) {
                console.error('Response data:', error.response.data);
            }
            return null;
        }
    },

    /**
     * Send image to backend OCR endpoint
     */
    async sendImageToOCR(filePath, filename, metadata) {
        try {
            console.log(`🔄 Sending image to OCR API: ${API_URL}/api/whatsapp/ocr`);

            const formData = new FormData();
            formData.append('image', fs.createReadStream(filePath), filename);
            formData.append('sender', metadata.sender);
            formData.append('sender_number', metadata.sender_number);
            formData.append('group_name', metadata.group_name);
            formData.append('group_id', metadata.group_id);
            formData.append('timestamp', metadata.timestamp);
            formData.append('message_id', metadata.message_id);

            const response = await axios.post(`${API_URL}/api/whatsapp/ocr`, formData, {
                headers: {
                    ...formData.getHeaders(),
                    'X-Webhook-Secret': WEBHOOK_SECRET
                },
                timeout: 30000, // OCR takes longer
                maxBodyLength: Infinity,
                maxContentLength: Infinity
            });

            return response.data;
        } catch (error) {
            console.error('❌ OCR API error:', error.message);
            if (error.response) {
                return error.response.data;
            }
            throw error;
        }
    },

    /**
     * Get debt summary (Direct API call optimization)
     */
    async getDebts() {
        try {
            console.log(`🌐 Fetching debts from API: ${API_URL}/api/debt`);
            const response = await apiClient.get('/api/debt');
            if (response.data && response.data.success) {
                return response.data.debts || [];
            }
            return [];
        } catch (error) {
            console.error('❌ Error getting debts:', error.message);
            return [];
        }
    },

    /**
     * Sync groups to backend
     */
    async syncGroups(groups) {
        try {
            console.log(`🌐 Syncing ${groups.length} groups to backend...`);
            const response = await apiClient.post('/api/whatsapp/sync-groups', { groups });
            return response.data;
        } catch (error) {
            console.error('❌ Error syncing groups:', error.message);
            return null;
        }
    },

    /**
     * Get recurring paylater list
     */
    async getRecurringList(search = 'paylater') {
        try {
            const query = search ? `?search=${encodeURIComponent(search)}` : '';
            console.log(`🌐 Fetching recurring list from API: ${API_URL}/api/whatsapp/recurring-list${query}`);
            const response = await apiClient.get(`/api/whatsapp/recurring-list${query}`);
            if (response.data && response.data.success) {
                return response.data;
            }
            return { success: false, recurring: [], reply_message: '🔄 *Recurring Paylater*\n• Belum ada data yang cocok' };
        } catch (error) {
            console.error('❌ Error getting recurring list:', error.message);
            return { success: false, recurring: [], reply_message: 'Maaf, gagal ambil daftar recurring.' };
        }
    },

    /**
     * Ask Financial Assistant (Q&A)
     */
    async askQuestion(question) {
        try {
            console.log(`🌐 Asking Q&A: "${question}"`);
            const response = await apiClient.post('/api/qna/ask', { question });
            if (response.data && response.data.answer) {
                return response.data.answer;
            }
            return "Maaf, terjadi kesalahan saat menghubungi asisten.";
        } catch (error) {
            console.error('❌ Error asking Q&A:', error.message);
            return "Maaf, asisten sedang tidak dapat dihubungi saat ini.";
        }
    }
};

module.exports = ApiService;

