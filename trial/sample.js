/**
 * Sample JavaScript module for testing AutoDoc.
 * @module sample
 */

const crypto = require('crypto');
const fs = require('fs').promises;

/**
 * Configuration options for the API client.
 * @typedef {Object} ApiConfig
 * @property {string} baseUrl - The base URL for API requests
 * @property {number} timeout - Request timeout in milliseconds
 * @property {Object} headers - Default headers to include
 * @property {boolean} retryEnabled - Whether to retry failed requests
 */

/**
 * API client for making HTTP requests.
 */
/**
 */
class ApiClient {
    constructor(config = {}) {
        this.baseUrl = config.baseUrl || 'https://api.example.com';
        this.timeout = config.timeout || 5000;
        this.headers = config.headers || {};
        this.retryEnabled = config.retryEnabled !== false;
        this.requestCount = 0;
    }

    async get(endpoint, params = {}) {
/**
 * @autodoc-generated
 * 
 * /**
 *  * ApiClient - Description of ApiClient
 *  *
 * 
 *  * @returns {*} Description of return value
 *  * @example
 *  * const result = ApiClient();
 *  */
 */
        const url = this._buildUrl(endpoint, params);
        return this._request('GET', url);
    }

    async post(endpoint, data = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        return this._request('POST', url, data);
    }

    _buildUrl(endpoint, params) {
        const url = new URL(endpoint, this.baseUrl);
        Object.entries(params).forEach(([key, value]) => {
            url.searchParams.append(key, value);
        });
        return url.toString();
    }

    async _request(method, url, data = null) {
        this.requestCount++;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...this.headers
            },
            timeout: this.timeout
        };
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            if (this.retryEnabled && this.requestCount < 3) {
                return this._request(method, url, data);
            }
            throw error;
        }
    }
}

function hashPassword(password, salt = null) {
    if (!salt) {
        salt = crypto.randomBytes(16).toString('hex');
    }
    const hash = crypto.pbkdf2Sync(password, salt, 100000, 64, 'sha512');
    return {
        hash: hash.toString('hex'),
        salt: salt
    };
}

function validateEmail(email) {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return pattern.test(email);
}

async function readJsonFile(filePath) {
    const data = await fs.readFile(filePath, 'utf8');
    return JSON.parse(data);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

module.exports = {
    ApiClient,
    hashPassword,
    validateEmail,
    readJsonFile,
    debounce
};
