/**
 * @autodoc-generated
 *
 * User - Description of User
 *
 * This function handles user operations.
 *
 * @returns {*} Description of return value
 * @example
 * const result = User();
 * console.log(result);
 */
interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'guest';
}

/**
 * @autodoc-generated
 *
 * QueryOptions - Description of QueryOptions
 *
 * This function handles queryoptions operations.
 *
 * @returns {*} Description of return value
 * @example
 * const result = QueryOptions();
 * console.log(result);
 */
interface QueryOptions {
  limit?: number;
  offset?: number;
  sortBy?: keyof User;
  order?: 'asc' | 'desc';
}

/**
 * @autodoc-generated
 *
 * DataService - Description of DataService
 *
 * This class handles dataservice operations.
 *
 * @returns {*} Description of return value
 * @example
 * const result = DataService();
 * console.log(result);
 */
export class DataService {
  private users: Map<string, User> = new Map();
  private cache: Map<string, any> = new Map();

  constructor(initialData?: User[]) {
    if (initialData) {
      initialData.forEach(user => this.users.set(user.id, user));
    }
  }

  async findById(id: string): Promise<User | null> {
    const cacheKey = `user:${id}`;
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    const user = this.users.get(id) || null;
    if (user) {
      this.cache.set(cacheKey, user);
    }
    return user;
  }

  async findAll(options: QueryOptions = {}): Promise<User[]> {
    const { limit = 10, offset = 0, sortBy = 'name', order = 'asc' } = options;

    let results = Array.from(this.users.values());

    results.sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      const comparison = String(aVal).localeCompare(String(bVal));
      return order === 'asc' ? comparison : -comparison;
    });

    return results.slice(offset, offset + limit);
  }

  async create(userData: Omit<User, 'id'>): Promise<User> {
    const id = this.generateId();
    const user: User = { ...userData, id };
    this.users.set(id, user);
    return user;
  }

  private generateId(): string {
    return Math.random().toString(36).substring(2, 15);
  }
}

export type { User, QueryOptions };
