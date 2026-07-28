SELECT id, name FROM workflow_entity WHERE nodes::text LIKE '%http://api%' OR nodes::text LIKE '%http://localhost%' OR nodes::text LIKE '%http://cartorio%';
