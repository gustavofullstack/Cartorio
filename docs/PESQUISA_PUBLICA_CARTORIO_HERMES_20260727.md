# Pesquisa publica para contexto do Hermes

**Escopo:** informacoes institucionais e de atendimento publicamente
disponiveis sobre o 2o Tabelionato de Notas de Uberlandia/MG. Este arquivo nao
e fonte juridica, cadastro oficial nem base de prospeccao.

## Perfil canonico para atendimento

| Campo | Valor para o Hermes | Confianca | Uso permitido |
|---|---|---:|---|
| Nome | 2o Tabelionato de Notas de Uberlandia/MG; alias: 2o Oficio de Notas | alta | identificacao e saudacao |
| CNS | 05.799-2 | media-alta | desambiguacao interna; nao inferir outros numeros a partir de formatacao de diretorio |
| Atribuicao | Notas | alta | triagem de servicos |
| Endereco | Rua Cel. Antonio Alves Pereira, 850, Centro, Uberlandia/MG | media-alta | informar com pedido de confirmacao por telefone antes de deslocamento |
| Telefone | (34) 3216-0252 | media | encaminhamento ao atendimento humano |
| Horario | segunda a sexta, 09h as 17h | media | informar como referencia; confirmar feriados e excecoes |
| Titular | Djalma Pizarro | media-alta | somente contexto institucional, nunca para aconselhamento ou dados pessoais |
| Substitutos atuais | Felipe Pizarro, Alexandra Jose Beicker | alta | contexto institucional; Victor Hugo Bianchini Pizarro nao integra mais o quadro |

## Hierarquia de fontes

1. Norma, portaria, tribunal, CNJ e canal institucional: fonte primária.
2. Associacoes notariais: contexto institucional secundario.
3. Diretorios comerciais: apenas corroboracao; podem estar desatualizados ou
   conter erros de formatacao.

As fontes externas consultadas apresentam o CNS, o endereco e o titular de
forma consistente em mais de um diretorio. O eCartorios tambem exibe esses
campos e declara usar dados publicos da Justica Aberta/CNJ. Porem, diretorios
divergem em CEP, horario, data de atualizacao, telefone complementar,
substituto e formatacao de CNPJ. Portanto, estes ultimos nao devem ser
afirmados pelo bot sem confirmacao humana ou fonte institucional atualizada.

## Conhecimento aprovado para respostas do agente

- O cartorio e de **Notas**: autenticacao, reconhecimento de firma,
  procuracoes, escrituras, atas notariais e testamentos sao intencoes de
  triagem, nunca promessa de que o ato pode ser concluido sem analise.
- O bot pode explicar, em linguagem simples, a diferenca entre autenticacao de
  copia e reconhecimento de firma, pedir o servico desejado e encaminhar para
  um escrevente em caso de duvida, urgencia, documento ou ato complexo.
- Valores somente saem do catalogo versionado da tabela MG e dentro do escopo
  de consulta direta; atos compostos continuam em HITL.
- Para endereco, horario, documentos exigidos, custo final, disponibilidade ou
  identidade de quem atendera, o bot deve usar linguagem condicional e oferecer
  confirmacao humana quando necessario.

## Intencoes e aliases sugeridos

| Intencao | Sinonimos publicos uteis | Resultado seguro |
|---|---|---|
| autenticacao | copia autenticada, autenticar documento | explicar finalidade; confirmar quantidade de folhas no humano |
| firma | reconhecer assinatura, ficha de firma, autenticidade, semelhanca | explicar triagem; nunca declarar que a firma esta aberta |
| procuracao | poderes, substabelecimento | coletar finalidade sem dado pessoal; HITL para conteudo |
| escritura | compra e venda, doacao, inventario, divorcio | HITL obrigatorio |
| ata notarial | constatacao, prova digital | HITL obrigatorio |
| testamento | testamento publico | HITL obrigatorio |
| contato | endereco, telefone, horario, como chegar | informar referencia e oferecer confirmacao |

## Nao inserir no conhecimento do Hermes

- Credenciais, chaves de API, tokens, enderecos de infraestrutura ou portas.
- CNPJ, e-mail, telefone alternativo, CEP, quadro de funcionarios e datas
  historicas com divergencia entre diretorios.
- Dados pessoais, perfilamento, listas de pessoas, idade, CPF parcial,
  contatos para disparo, ou cruzamento de bases.
- Materias processuais, decisoes disciplinares ou mencoes reputacionais: nao
  respondem a uma necessidade de atendimento e nao devem compor a memoria do
  chatbot.

## Evidencias publicas verificadas em 2026-07-27

- Diretorio Cartorio.net: CNS 05.799-2, atribuicao Notas, endereco e titular.
  <https://cartorio.net/cartorio/2o-tabelionato-de-notas-de-uberlandia-mg-57992/>
- Diretorio Cartorio no Brasil: nome, atribuicao, endereco, telefone e titular;
  usado apenas como corroboracao, pois nao e fonte oficial.
  <https://cartorionobrasil.com.br/cartorio-em-minas-gerais/cartorio-em-uberlandia-minas-gerais-2-tabelionato-de-notas/>
- ANOREG/BR registra uma mencao institucional publica ao tabeliao em evento
  regional; nao e fonte de dados de atendimento.
  <https://www.anoreg.org.br/site/encontro-regional-da-serjus-anoreg-mg-e-realizado-no-dia-9-de-abril-em-uberlandia/>
- eCartorios corrobora CNS, atribuicao, endereco, horario de referencia e
  titular; e um diretorio, nao uma fonte primaria.
  <https://ecartorios.com/centro-uberlandia-38400112/>
- A tabela de emolumentos segue sua cadeia de proveniencia separada em
  `docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md`.

## Cobertura dos links recebidos

| Fonte | Resultado | Uso no pacote |
|---|---|---|
| Cartorio.info, Certidao Online Brasil, Cartorio no Brasil, eCartorios e Cartorio.net | acessiveis | corroboracao com confianca limitada |
| Gazeta do Povo e Jusbrasil | indisponiveis na consulta automatizada | nao usados como evidencia |
| Link de Registro de Imoveis | aponta para outra serventia | excluido por desambiguacao |
| Diretorio "Cartorio em Sao Paulo" | pagina de busca sem registro verificavel da serventia | excluido |
| Instagram | nao coletado; plataforma autenticada/volatil | fora da base do Hermes |
