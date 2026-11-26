create table aviso (
    tarefa_id  uuid primary key,
    empresa    varchar(80)  not null,
    titulo     varchar(120) not null,
    vencida_em timestamp with time zone not null,
    criado_em  timestamp with time zone not null
);

create index idx_aviso_empresa on aviso (empresa);
