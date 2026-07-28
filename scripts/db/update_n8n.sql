UPDATE workflow_entity 
SET nodes = (
  REPLACE(
    REPLACE(
      REPLACE(
        REPLACE(
          nodes::text, 
          'http://api:8000', 'https://api.2notasudi.com.br'
        ), 
        'http://localhost:8000', 'https://api.2notasudi.com.br'
      ), 
      'http://cartorio:8000', 'https://api.2notasudi.com.br'
    ), 
    'http://host.docker.internal:8000', 'https://api.2notasudi.com.br'
  )
)::json
WHERE nodes::text LIKE '%http://api:8000%' 
   OR nodes::text LIKE '%http://localhost:8000%' 
   OR nodes::text LIKE '%http://cartorio:8000%' 
   OR nodes::text LIKE '%http://host.docker.internal:8000%';
