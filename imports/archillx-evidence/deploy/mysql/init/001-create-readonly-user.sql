-- Optional helper user for BI/read-only access
CREATE USER IF NOT EXISTS 'archillx_ro'@'%' IDENTIFIED BY 'change-me-readonly';
GRANT SELECT ON archillx.* TO 'archillx_ro'@'%';
FLUSH PRIVILEGES;
