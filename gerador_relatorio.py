"""
gerador_relatorio.py
Gera relatório em PDF com as métricas do processamento de dados.
Retorna os bytes do arquivo PDF para o Streamlit disponibilizar o download.
"""

import io
import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def gerar_pdf_profissional(metricas: dict) -> bytes | None:
    """
    Gera um relatório em PDF profissional com as métricas do processamento.
    Inclui descrição detalhada de decisões, processamento, entradas e saídas.
    
    Args:
        metricas: dicionário contendo os dados do processamento
        
    Returns:
        bytes do arquivo PDF ou None em caso de erro
    """
    try:
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4,
                               rightMargin=0.75*inch, leftMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        titulo_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0d0d0d'),
            spaceAfter=12,
            alignment=1
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#e05c5c'),
            spaceAfter=8,
            spaceBefore=12
        )
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#2a2a2a'),
            spaceAfter=6,
            spaceBefore=8
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=6,
            alignment=4
        )
        
        # ─────── CAPA ─────────
        story.append(Paragraph("🩸 Relatório de Tratamento de Dados", titulo_style))
        story.append(Paragraph("SIM/DATASUS — Óbitos por Leucemia (CIDs C91–C93)", styles['Normal']))
        story.append(Spacer(1, 0.4*inch))
        
        # Data e hora
        data_proc = metricas.get("data_processamento", "N/A")
        story.append(Paragraph(f"<b>Gerado em:</b> {data_proc}", normal_style))
        story.append(Spacer(1, 0.3*inch))
        
        # ─────── RESUMO EXECUTIVO ─────────
        story.append(Paragraph("📋 Resumo Executivo", heading_style))
        story.append(Paragraph(
            "Este relatório descreve o processamento automatizado de dados de óbitos por leucemia "
            "obtidos do Sistema de Informações sobre Mortalidade (SIM) do DATASUS. O objetivo foi "
            "selecionar, limpar e padronizar registros de óbitos, removendo dados incompletos e "
            "mantendo apenas os casos classificados como leucemia (códigos C91, C92 e C93 da CID-10).",
            normal_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # ─────── 1. ENTRADA (ARQUIVO ORIGINAL) ─────────
        story.append(Paragraph("1️⃣ ENTRADA: Arquivo Original", heading_style))
        
        nome_arq = metricas.get("nome_arquivo", "N/A")
        tamanho = metricas.get("tamanho_mb", 0)
        modo = metricas.get("modo_leitura", "N/A")
        lin_ini = metricas.get("linhas_inicial", 0)
        col_ini = metricas.get("colunas_inicial", 0)
        
        story.append(Paragraph(
            f"<b>Nome do arquivo:</b> {nome_arq}<br/>"
            f"<b>Tamanho:</b> {tamanho} MB<br/>"
            f"<b>Formato:</b> {modo}<br/>"
            f"<b>Registros originais:</b> {lin_ini:,} linhas<br/>"
            f"<b>Colunas disponíveis:</b> {col_ini} campos",
            normal_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # ─────── 2. PROCESSAMENTO E DECISÕES ─────────
        story.append(Paragraph("2️⃣ PROCESSAMENTO: Etapas Executadas", heading_style))
        
        story.append(Paragraph("<b>O que foi feito:</b>", subheading_style))
        story.append(Paragraph(
            "O sistema aplicou uma série de transformações para garantir a qualidade dos dados. "
            "Cada etapa foi cuidadosamente projetada para remover anomalias e padronizar informações.",
            normal_style
        ))
        story.append(Spacer(1, 0.15*inch))
        
        # Descrição textual das etapas (em vez de tabela)
        etapas_texto = """
<b>1. Seleção de Colunas</b><br/>
Mantidas apenas as 13 colunas relevantes para análise: UF naturalidade, Cod Municipio Natural, idade, sexo, raça/cor, estado civil, escolaridade, ocupação, Municipio de residência, local de ocorrência e causa básica. Colunas desnecessárias foram removidas para reduzir ruído e facilitar a análise.<br/><br/>

<b>2. Filtro por CID (Leucemia)</b><br/>
Aplicado filtro robusto para manter <u>exclusivamente</u> registros com códigos C91, C92 ou C93 (leucemia). Todos os outros óbitos foram automaticamente removidos. Isso garante que o dataset contém apenas dados sobre leucemia.<br/><br/>

<b>3. Remoção de Valores Ausentes</b><br/>
Eliminados registros com campos vazios ou não preenchidos. Dados incompletos prejudicam análises estatísticas e podem levar a conclusões incorretas. Todos os registros mantidos têm informação completa em todos os campos.<br/><br/>

<b>4. Conversão de SEXO</b><br/>
Convertidos códigos numéricos para texto legível: 1=Masculino, 2=Feminino, entre outros. Facilita a interpretação dos resultados.<br/><br/>

<b>5. Conversão de RAÇA/COR</b><br/>
Padronizadas categorias: 1=Branca, 2=Preta, 3=Amarela, 4=Parda, 5=Indígena. Permite análises demográficas comparativas.<br/><br/>

<b>6. Conversão de ESTADO CIVIL</b><br/>
Convertidos códigos para texto: 1=Solteiro, 2=Casado, 3=Viúvo, 4=Separado, 5=Não informado. Melhora legibilidade dos dados.<br/><br/>

<b>7. Cálculo de IDADE</b><br/>
Convertida idade de dias/horas para anos decimais. Permite análises por faixa etária e correlações com idade média dos óbitos.<br/><br/>

<b>8. Conversão de ESCOLARIDADE</b><br/>
Padronizadas categorias educacionais: Nenhuma, 1º-4º série, 5º-8º série, Ensino Médio, Superior, etc. Mantém consistência nas categorias educacionais.<br/><br/>

<b>9. Criação de UF (Estados)</b><br/>
Extraídos e convertidos códigos de Estado (UF) de naturalidade e ocorrência para siglas (SP, RJ, MG, etc.). Permite análises geográficas por estado.<br/><br/>

<b>10. Descrição de LOCAL DE OCORRÊNCIA</b><br/>
Convertidos códigos para texto: Hospital, Domicílio, Via Pública, Outros. Identifica onde os óbitos ocorreram.
"""
        story.append(Paragraph(etapas_texto, normal_style))
        story.append(Spacer(1, 0.2*inch))
        
        # ─────── 3. CRITÉRIOS DE FILTRAGEM ─────────
        story.append(Paragraph("3️⃣ CRITÉRIOS DE FILTRAGEM: O Que Foi Removido", heading_style))
        
        lin_fin = metricas.get("linhas_final", 0)
        lin_removidas = lin_ini - lin_fin
        reducao = metricas.get("reducao_pct", 0)
        
        story.append(Paragraph(
            f"<b>Registros removidos:</b> {lin_removidas:,} ({reducao}% do total)<br/><br/>"
            "<b>Motivos da remoção:</b><br/>"
            "• Registros com CID diferente de C91, C92 ou C93 (leucemia)<br/>"
            "• Registros com informações incompletas (campos vazios)<br/>"
            "• Registros com dados inválidos ou inconsistentes<br/>"
            "• Registros duplicados ou com valores não interpretáveis",
            normal_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # ─────── 4. SAÍDA ─────────
        story.append(Paragraph("4️⃣ SAÍDA: Resultado Final", heading_style))
        
        col_fin = metricas.get("colunas_final", 0)
        cids = metricas.get("cids_encontrados", [])
        
        # Tabela de estatísticas
        dados_stats = [
            ["Métrica", "Valor"],
            ["Registros iniciais", f"{lin_ini:,}"],
            ["Registros removidos", f"{lin_removidas:,}"],
            ["Registros finais (válidos)", f"{lin_fin:,}"],
            ["Taxa de redução", f"{reducao}%"],
            ["Colunas no resultado", f"{col_fin}"],
            ["CIDs únicos encontrados", f"{len(cids)}"],
        ]
        
        table_stats = Table(dados_stats, colWidths=[3.2*inch, 2.3*inch])
        table_stats.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e05c5c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#999999')),
            ('LINEBELOW', (0, 0), (-1, 0), 2.5, colors.HexColor('#d04040')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        story.append(table_stats)
        story.append(Spacer(1, 0.2*inch))
        
        # CIDs encontrados
        story.append(Paragraph("<b>Tipos de leucemia identificados (CIDs):</b>", subheading_style))
        if cids:
            cids_text = ", ".join(sorted(cids))
            story.append(Paragraph(f"{cids_text}", normal_style))
        else:
            story.append(Paragraph("Nenhum CID encontrado.", normal_style))
        story.append(Spacer(1, 0.2*inch))
        
        # ─────── 5. INTERPRETAÇÃO ─────────
        story.append(Paragraph("5️⃣ INTERPRETAÇÃO: O Que Isto Significa", heading_style))
        
        story.append(Paragraph(
            f"<b>✓ Dados prontos para análise:</b> O dataset final contém {lin_fin:,} registros "
            f"de óbitos por leucemia com informações padronizadas.<br/><br/>"
            f"<b>✓ Foco nas CID:</b> A remoção de {reducao}% dos registros fora do "
            "escopo da pesquisa.<br/><br/>"
            f"<b>✓ Informações demográficas:</b> Sexo, raça/cor, estado civil e escolaridade foram "
            "padronizados para facilitar análises comparativas.<br/><br/>"
            f"<b>✓ Localização geográfica:</b> Estados de naturalidade e ocorrência foram "
            "identificados para análises regionais.<br/><br/>"
            f"<b>✓ Distribuição etária:</b> Idade foi convertida para anos, permitindo análises "
            "de sobrevida e incidência por faixa etária.",
            normal_style
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # Rodapé
        story.append(Paragraph("―" * 100, normal_style))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(
            "<i>Este relatório foi gerado automaticamente pelo sistema SIM · Leucemia. "
            "O Processamento de dados é feito de forma Experimental e pode conter erros "
            "Cheque as informações com a base de dados original!.</i>",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=4)
        ))
        
        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return None