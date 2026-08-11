# ER Diagram: {{project_name}}

```mermaid
erDiagram
    %% === Core Entities ===

    USER {
        uuid id PK
        string email UK
        string password_hash
        string name
        string role
        timestamp created_at
        timestamp updated_at
    }

    %% === Relationships ===
    %% USER ||--o{ POST : "creates"

    %% === Indexes ===
    %% - USER.email: unique index for login lookup
```

## Legend
- **PK**: Primary Key
- **UK**: Unique Key
- **FK**: Foreign Key
- **||--o{**: One-to-Many
- **}o--o{**: Many-to-Many
- **||--||**: One-to-One

## Notes
- All tables use UUID primary keys by default
- All tables include created_at and updated_at timestamps
- Soft delete via deleted_at timestamp where applicable
