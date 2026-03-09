const axios = require('axios');
const EventEmitter = require('events');

/**
 * @autodoc-generated
 *
 * ApiClient - Description of ApiClient
 *
 * This class handles apiclient operations.
 *
 * @returns {*} Description of return value
 * @example
 * const result = ApiClient();
 * console.log(result);
 */
class ApiClient extends EventEmitter {
  constructor(baseURL, apiKey) {
    super();
    this.client = axios.create({
      baseURL,
      headers: { 'Authorization': `Bearer ${apiKey}` }
    });
    this.retryCount = 3;
    this.retryDelay = 1000;
  }

  async get(endpoint, params = {}) {
    return this._request('GET', endpoint, { params });
  }

  async post(endpoint, data = {}) {
    return this._request('POST', endpoint, { data });
  }

  async _request(method, endpoint, config) {
    for (let attempt = 0; attempt < this.retryCount; attempt++) {
      try {
        const response = await this.client.request({
          method,
          url: endpoint,
          ...config
        });
        this.emit('success', { endpoint, attempt });
        return response.data;
      } catch (error) {
        if (attempt === this.retryCount - 1) {
          this.emit('error', { endpoint, error });
          throw error;
        }
        await this._sleep(this.retryDelay * Math.pow(2, attempt));
      }
    }
  }

  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

module.exports = ApiClient;
