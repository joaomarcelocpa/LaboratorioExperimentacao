create table chave_idempotencia (
    chave     varchar(200) primary key,
    impressao varchar(2600) not null,
    tarefa_id uuid          not null
);
