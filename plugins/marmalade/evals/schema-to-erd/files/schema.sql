CREATE TABLE tenants (
  id uuid PRIMARY KEY,
  slug varchar(63) NOT NULL UNIQUE
);
CREATE TABLE users (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  email varchar(255) NOT NULL UNIQUE,
  manager_id uuid REFERENCES users(id)
);
CREATE TABLE projects (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  owner_id uuid REFERENCES users(id),
  name varchar(200) NOT NULL
);
CREATE TABLE project_members (
  project_id uuid NOT NULL REFERENCES projects(id),
  user_id uuid NOT NULL REFERENCES users(id),
  role varchar(32) NOT NULL,
  PRIMARY KEY (project_id, user_id)
);
