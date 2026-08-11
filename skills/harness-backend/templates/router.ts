import { Request, Response, NextFunction } from 'express';
import { {{EntityName}}Service } from '../services/{{entity-name}}.service';
import { Create{{EntityName}}Dto, Update{{EntityName}}Dto } from '../models/{{entity-name}}.model';

export class {{EntityName}}Controller {
  constructor(private service: {{EntityName}}Service) {}

  list = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const page = parseInt(req.query.page as string) || 1;
      const limit = parseInt(req.query.limit as string) || 20;
      const result = await this.service.list(page, limit);
      res.json({
        success: true,
        data: result.data,
        meta: { page, limit, total: result.total },
      });
    } catch (error) {
      next(error);
    }
  };

  getById = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const entity = await this.service.getById(req.params.id);
      res.json({ success: true, data: entity });
    } catch (error) {
      next(error);
    }
  };

  create = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const dto: Create{{EntityName}}Dto = req.body;
      const entity = await this.service.create(dto);
      res.status(201).json({ success: true, data: entity });
    } catch (error) {
      next(error);
    }
  };

  update = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const dto: Update{{EntityName}}Dto = req.body;
      const entity = await this.service.update(req.params.id, dto);
      res.json({ success: true, data: entity });
    } catch (error) {
      next(error);
    }
  };

  delete = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      await this.service.delete(req.params.id);
      res.status(204).send();
    } catch (error) {
      next(error);
    }
  };
}
