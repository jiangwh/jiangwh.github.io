# Docker start pg

```bash
docker run --name pg -v dv_pgdata:/Users/jiangwh/vm/pg -e POSTGRES_PASSWORD=admin -p 5432:5432 -d postgres:12
```

