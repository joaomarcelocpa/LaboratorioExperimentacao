create table tarefa (
    id          uuid primary key,
    titulo      varchar(120)  not null,
    descricao   varchar(2000),
    responsavel varchar(80)   not null,
    vencimento  timestamp with time zone   not null,
    status      varchar(20)   not null,
    criada_em   timestamp with time zone   not null
);
