import { Router } from 'express';
import { {{EntityName}}Controller } from '../controllers/{{entity-name}}.controller';
import { authenticate } from '../middleware/auth';
import { validate } from '../middleware/validate';
import { {{EntityName}}Schema } from '../schemas/{{entity-name}}.schema';

const router = Router();
const controller = new {{EntityName}}Controller();

// CRUD routes
router.get('/', authenticate, controller.list);
router.get('/:id', authenticate, controller.getById);
router.post('/', authenticate, validate({{EntityName}}Schema), controller.create);
router.put('/:id', authenticate, validate({{EntityName}}Schema), controller.update);
router.delete('/:id', authenticate, controller.delete);

export default router;
