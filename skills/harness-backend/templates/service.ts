import { {{EntityName}}Repository } from '../repositories/{{entity-name}}.repository';
import { {{EntityName}}, Create{{EntityName}}Dto, Update{{EntityName}}Dto } from '../models/{{entity-name}}.model';
import { NotFoundError, ValidationError } from '../utils/errors';

export class {{EntityName}}Service {
  constructor(private repository: {{EntityName}}Repository) {}

  async list(page: number = 1, limit: number = 20): Promise<{ data: {{EntityName}}[]; total: number }> {
    const offset = (page - 1) * limit;
    const [data, total] = await Promise.all([
      this.repository.findAll({ offset, limit }),
      this.repository.count(),
    ]);
    return { data, total };
  }

  async getById(id: string): Promise<{{EntityName}}> {
    const entity = await this.repository.findById(id);
    if (!entity) {
      throw new NotFoundError(`{{EntityName}} not found: ${id}`);
    }
    return entity;
  }

  async create(dto: Create{{EntityName}}Dto): Promise<{{EntityName}}> {
    return this.repository.create(dto);
  }

  async update(id: string, dto: Update{{EntityName}}Dto): Promise<{{EntityName}}> {
    await this.getById(id); // verify exists
    return this.repository.update(id, dto);
  }

  async delete(id: string): Promise<void> {
    await this.getById(id); // verify exists
    await this.repository.delete(id);
  }
}
