-- Creates the separate test database used by the `tests` compose service.
-- Runs only on first initialisation of the postgres data volume.
-- The owner is the POSTGRES_USER that initialised this cluster.
SELECT 'CREATE DATABASE varagh_test OWNER ' || current_user
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'varagh_test')\gexec
