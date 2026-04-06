/**
 * relatorio.js
 * Gera um relatório Word (.docx) legível para não-programadores.
 * Uso: node relatorio.js '<json_string>'
 */

const {
    Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
    HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
    LevelFormat, PageNumber, Footer, Header,
} = require("docx");
const fs = require("fs");

const dados = JSON.parse(process.argv[2]);
const {
    nome_arquivo, tamanho_mb, linhas_inicial, colunas_inicial,
    linhas_final, colunas_final, reducao_pct,
    cids_encontrados, modo_leitura, data_processamento,
} = dados;

// ─── Helpers ──────────────────────────────────────────────────────────────────
const AZUL   = "1B4F8A";
const CINZA  = "F5F5F5";
const BORDA  = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDAS = { top: BORDA, bottom: BORDA, left: BORDA, right: BORDA };
const MARGEM = { top: 80, bottom: 80, left: 140, right: 140 };
const W      = 9360;

const bold  = (t, s=22) => new TextRun({ text:t, bold:true, size:s, font:"Arial" });
const txt   = (t, s=22, cor) => new TextRun({ text:t, size:s, font:"Arial", color: cor||"222222" });
const par   = (children, opts={}) => new Paragraph({ children, ...opts });
const vazio = () => par([txt(" ")], { spacing:{ after:100 } });

function secao(titulo) {
    return new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun({ text:titulo, bold:true, size:26, font:"Arial", color:AZUL })],
        spacing: { before:320, after:160 },
        border: { bottom:{ style:BorderStyle.SINGLE, size:6, color:AZUL, space:1 } },
    });
}

function mkTabela(linhas) {
    const n = linhas[0].length;
    const col_w = Math.floor(W / n);
    return new Table({
        width: { size:W, type:WidthType.DXA },
        columnWidths: Array(n).fill(col_w),
        rows: linhas.map((row, ri) =>
            new TableRow({
                children: row.map((cel, ci) =>
                    new TableCell({
                        borders: BORDAS,
                        width: { size:col_w, type:WidthType.DXA },
                        margins: MARGEM,
                        shading: ri===0
                            ? { fill:AZUL,  type:ShadingType.CLEAR }
                            : ri%2===0 ? { fill:CINZA, type:ShadingType.CLEAR } : {},
                        children: [par([new TextRun({
                            text: String(cel), bold: ri===0,
                            size:20, font:"Arial",
                            color: ri===0 ? "FFFFFF" : "222222",
                        })])],
                    })
                ),
            })
        ),
    });
}

function item(t) {
    return new Paragraph({
        numbering: { reference:"bullets", level:0 },
        children: [txt(t)],
        spacing: { after:60 },
    });
}

// ─── Passos do tratamento ─────────────────────────────────────────────────────
const passos = [
    ["1","Seleção de colunas",
     "Das diversas colunas presentes no arquivo original, foram mantidas apenas as 13 variáveis relevantes para a análise de leucemia. Isso reduz o volume de dados e facilita a análise posterior."],
    ["2","Filtro por CID-10 (Leucemia)",
     "Foram mantidos apenas os registros cuja causa básica do óbito (CAUSABAS) corresponde a leucemia: C91 (linfoide), C92 (mieloide) e C93 (monocítica). Todos os demais óbitos foram descartados."],
    ["3","Remoção de dados ausentes",
     "Linhas com qualquer campo vazio ou não informado foram removidas para garantir a qualidade e confiabilidade das análises. Registros incompletos podem distorcer resultados estatísticos."],
    ["4","Conversão de Sexo",
     "O campo SEXO original usa códigos numéricos (1=Masculino, 2=Feminino). Foi convertido para texto legível. Valores fora desse padrão foram mantidos sem alteração."],
    ["5","Conversão de Raça/Cor",
     "O campo RACACOR usa códigos numéricos conforme classificação do IBGE: 1=Branca, 2=Preta, 3=Amarela, 4=Parda, 5=Indígena. Foi convertido para o texto correspondente."],
    ["6","Conversão de Estado Civil",
     "O campo ESTCIV usa códigos: 1=Solteiro, 2=Casado, 3=Viúvo, 4=Divorciado, 5=União Estável, 9=Ignorado. Foi convertido para texto descritivo."],
    ["7","Conversão de Idade",
     "O campo IDADE do SIM usa formato especial de 3 dígitos: o 1º indica a unidade (1=minutos, 2=horas, 3=meses, 4=anos, 5=>100 anos, 9=ignorado) e os 2 últimos o valor. Tudo foi convertido para anos decimais. Idades ignoradas foram removidas."],
    ["8","Conversão de Escolaridade",
     "O campo ESC2010 usa códigos: 0=Sem escolaridade, 1=Fund. I, 2=Fund. II, 3=Ensino Médio, 4=Superior incompleto, 5=Superior completo, 9=Ignorado. Convertido para texto descritivo."],
    ["9","Criação de UF de Naturalidade e Ocorrência",
     "Foram criadas duas novas colunas: UF_NATURAL (UF de nascimento, extraída de NATURAL) e UF_OCOR (UF onde ocorreu o óbito, extraída de CODMUNOCOR). Facilitam análises geográficas."],
    ["10","Descrição do Local de Ocorrência",
     "O campo LOCOCOR usa códigos: 1=Hospital, 2=Outro estab. de saúde, 3=Domicílio, 4=Via pública, 5=Outros, 6=Aldeia indígena, 9=Ignorado. Foi criada a coluna LOCOCOR_DESC com o texto correspondente."],
];

const colunasSel = [
    ["NATURAL","Naturalidade (código IBGE)"],
    ["CODMUNNATU","Código do município de naturalidade"],
    ["IDADE","Idade (convertida para anos decimais)"],
    ["SEXO","Sexo (convertido para texto)"],
    ["RACACOR","Raça/Cor (convertida para texto)"],
    ["ESTCIV","Estado Civil (convertido para texto)"],
    ["ESC2010","Escolaridade 2010 (convertida para texto)"],
    ["OCUP","Ocupação"],
    ["CODMUNRES","Município de residência"],
    ["LOCOCOR","Local de ocorrência (código original)"],
    ["CODMUNOCOR","Município de ocorrência"],
    ["CAUSABAS","Causa básica do óbito (CID-10)"],
    ["STDONOVA","Situação da Declaração de Óbito"],
];

// ─── Documento ────────────────────────────────────────────────────────────────
const doc = new Document({
    styles: {
        default: { document: { run: { font:"Arial", size:22 } } },
        paragraphStyles: [
            { id:"Heading1", name:"Heading 1", basedOn:"Normal", next:"Normal", quickFormat:true,
              run:{ size:36, bold:true, font:"Arial", color:AZUL },
              paragraph:{ spacing:{ before:0, after:240 }, outlineLevel:0 } },
            { id:"Heading2", name:"Heading 2", basedOn:"Normal", next:"Normal", quickFormat:true,
              run:{ size:26, bold:true, font:"Arial", color:AZUL },
              paragraph:{ spacing:{ before:320, after:160 }, outlineLevel:1 } },
        ],
    },
    numbering: {
        config:[{ reference:"bullets",
            levels:[{ level:0, format:LevelFormat.BULLET, text:"•",
                alignment:AlignmentType.LEFT,
                style:{ paragraph:{ indent:{ left:720, hanging:360 } } } }] }],
    },
    sections:[{
        properties:{
            page:{
                size:{ width:12240, height:15840 },
                margin:{ top:1440, right:1440, bottom:1440, left:1440 },
            },
        },
        headers:{ default: new Header({ children:[
            new Paragraph({
                children:[txt("Relatório de Tratamento de Dados — SIM/DATASUS · Leucemia", 18, "888888")],
                border:{ bottom:{ style:BorderStyle.SINGLE, size:4, color:"CCCCCC", space:1 } },
            }),
        ]}) },
        footers:{ default: new Footer({ children:[
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children:[ txt("Página ", 18, "888888"), new PageNumber() ],
            }),
        ]}) },
        children:[

            // Título
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children:[bold("Relatório de Tratamento de Dados", 36)],
                spacing:{ before:480, after:120 },
            }),
            par([bold("Sistema de Informações sobre Mortalidade (SIM/DATASUS)", 26)]),
            par([txt("Óbitos por Leucemia — CIDs C91, C92 e C93", 22, "555555")],
                { spacing:{ after:480 } }),

            // 1. Informações gerais
            secao("1. Informações Gerais"),
            vazio(),
            mkTabela([
                ["Item","Detalhe"],
                ["Arquivo processado", nome_arquivo],
                ["Tamanho do arquivo", `${tamanho_mb} MB`],
                ["Data e hora", data_processamento],
                ["Modo de leitura", modo_leitura],
            ]),
            vazio(),

            // 2. Resumo numérico
            secao("2. Resumo do Processamento"),
            vazio(),
            mkTabela([
                ["Indicador","Valor"],
                ["Registros no arquivo original", `${linhas_inicial.toLocaleString("pt-BR")} linhas`],
                ["Colunas no arquivo original",   `${colunas_inicial} colunas`],
                ["Registros após tratamento",     `${linhas_final.toLocaleString("pt-BR")} linhas`],
                ["Colunas após tratamento",       `${colunas_final} colunas`],
                ["Redução de registros",          `${reducao_pct}%`],
                ["Registros descartados",         `${(linhas_inicial-linhas_final).toLocaleString("pt-BR")} linhas`],
                ["CIDs de leucemia encontrados",  `${cids_encontrados.length} código(s)`],
            ]),
            vazio(),

            // 3. CIDs
            secao("3. Códigos CID-10 Encontrados"),
            par([txt("Foram identificados os seguintes códigos de leucemia: C91 = leucemia linfoide, C92 = mieloide, C93 = monocítica.")],
                { spacing:{ after:160 } }),
            ...cids_encontrados.map(c => item(c)),
            vazio(),

            // 4. Colunas
            secao("4. Variáveis Selecionadas para Análise"),
            par([txt("Das colunas disponíveis, foram mantidas apenas as listadas abaixo por serem relevantes para a análise epidemiológica de leucemia.")],
                { spacing:{ after:160 } }),
            mkTabela([["Coluna (nome técnico)","O que representa"], ...colunasSel]),
            vazio(),

            // 5. Passos
            secao("5. Decisões de Tratamento — Passo a Passo"),
            par([txt("A seguir estão descritas, em linguagem acessível, cada etapa do tratamento aplicado aos dados.")],
                { spacing:{ after:200 } }),
            ...passos.flatMap(([num, titulo, desc]) => [
                new Paragraph({
                    children:[bold(`Passo ${num} — ${titulo}`, 24)],
                    spacing:{ before:240, after:80 },
                }),
                par([txt(desc)], { spacing:{ after:160 } }),
            ]),

            // 6. O que mudou
            secao("6. O Que Mudou nos Dados"),
            par([txt("Após o tratamento, as seguintes transformações foram realizadas:")],
                { spacing:{ after:120 } }),
            item("SEXO: de código numérico para texto (Masculino, Feminino)"),
            item("RACACOR: de código numérico para texto (Branca, Preta, Amarela, Parda, Indígena)"),
            item("ESTCIV: de código numérico para texto (Solteiro, Casado, Viúvo, etc.)"),
            item("IDADE: de formato especial SIM para anos decimais"),
            item("ESC2010: de código numérico para descrição da escolaridade"),
            item("UF_NATURAL: coluna nova criada a partir do campo NATURAL"),
            item("UF_OCOR: coluna nova criada a partir de CODMUNOCOR"),
            item("LOCOCOR_DESC: coluna nova com descrição do local de ocorrência"),
            vazio(),

            // 7. Por que removidos
            secao("7. Por Que Alguns Registros Foram Removidos"),
            par([txt(`O arquivo original continha ${linhas_inicial.toLocaleString("pt-BR")} registros. Após o tratamento, restaram ${linhas_final.toLocaleString("pt-BR")} (redução de ${reducao_pct}%). Os registros foram removidos pelos seguintes motivos:`)],
                { spacing:{ after:120 } }),
            item("Causa básica diferente de leucemia (C91, C92, C93): registros fora do escopo da análise."),
            item("Campos obrigatórios em branco: registros incompletos distorcem análises estatísticas."),
            item("Idade com código ignorado (unidade=9): impossível realizar análises de faixa etária sem esse dado."),
            vazio(),

            // 8. Observações
            secao("8. Observações Finais"),
            par([txt("Este relatório foi gerado automaticamente. Os dados de saída estão prontos para análise em Excel, SPSS, R ou Python. Em caso de dúvidas sobre o processo, consulte o responsável técnico pelo sistema.")]),
        ],
    }],
});

Packer.toBuffer(doc).then(buf => {
    const saida = "/tmp/relatorio_tratamento.docx";
    fs.writeFileSync(saida, buf);
    process.stdout.write(saida);
});