-- Cadastro de clientes e fornecedores — base: Cadastro de Clientes e Fornecedores.txt
-- Confirmar encoding de Cliente_Fornecedor (filtro <> 1).
SELECT DISTINCT
    Entidades.ID_Filial,
    Entidades.ID_Entidade,
    Entidades.NomeEntidade,
    Entidades.RazaoSocialEntidade,
    Entidades.DtaCadastro,
    Entidades.Pessoa,
    Entidades.Endereco,
    Entidades.Bairro,
    Entidades.Cep,
    Entidades.CnpjCpf,
    Entidades.IeRg,
    Entidades.Fone,
    Entidades.Celular,
    Entidades.Email,
    Entidades.Categoria,
    Entidades.DiaVcto,
    Entidades.CODIGOENTIDADE,
    EmpresasEntidades.NomeEmpresasEntidades,
    Cidades.NomeCidade,
    TipoPgto,
    PrazoOperacional,
    Limite,
    Carencia
FROM Entidades
INNER JOIN Cidades
    ON Entidades.ID_Cidades = Cidades.ID_Cidades
    AND Entidades.ID_Filial = Cidades.ID_Filial
LEFT JOIN EmpresasEntidades
    ON Entidades.ID_EmpresasEntidades = EmpresasEntidades.ID_EmpresasEntidades
    AND Entidades.ID_Filial = EmpresasEntidades.ID_Filial
LEFT JOIN LISTANEGRACLIENTES
    ON LISTANEGRACLIENTES.ID_ENTIDADE = ENTIDADES.ID_ENTIDADE
    AND LISTANEGRACLIENTES.ID_DB = ENTIDADES.ID_FILIAL
WHERE Entidades.ID_FILIAL IN (12290, 5301, 16709, 2443)
    AND Entidades.Ativo = 1
    AND Cliente_Fornecedor <> 1
ORDER BY Entidades.ID_Filial, Entidades.ID_Entidade, Entidades.NomeEntidade;
