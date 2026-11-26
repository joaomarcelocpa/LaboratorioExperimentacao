alter table tarefa add column empresa varchar(80) default 'padrao' not null;

create index idx_tarefa_empresa_resp_status on tarefa (empresa, responsavel, status, vencimento);
create index idx_tarefa_empresa_venc on tarefa (empresa, vencimento);
