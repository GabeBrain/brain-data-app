# src/data_processing.py
import streamlit as st
import pandas as pd
import numpy as np
import re
import unicodedata
import json
from pathlib import Path
from datetime import datetime

# --- Dicionário de Mapeamento de Perguntas Alvo ---
perguntas_alvo_codigos = {
    "Código": ["Código"],
    "FE2P3": [
        "P1", "FE2P3", "Qual o seu Gênero?", "Gênero: (SOMENTE REGISTRAR)",
        "Gênero (anotar):", "Gênero (apenas anotar)"
    ],
    "FE2P5": [
        "P2.1", "FE2P5", "Qual é a sua idade?",
        "Qual sua idade por gentileza?",
        "Quantos anos o(a) Sr(a) tem? (RU e Espontânea)"
    ],
    "FE2P6": [
        "P2.2", "FE2P6", "Faixa etária: (SOMENTE REGISTRAR)",
        "Faixa etária (SOMENTE ANOTAR)", "Idade (anotar)",
        "Apenas anotar de acordo com a idade do entrevistado?"
    ],
    "FE2P7": [
        "E2.1", "FE2P7", "Em qual cidade você mora?",
        "Antes de iniciar a pesquisa, o(a) Sr(a) poderia dizer qual CIDADE que o(a) Sr(a) mora?",
        "Antes de iniciar, o(a) Sr(a) poderia dizer qual BAIRRO de CIDADE X que o(a) Sr(a) mora?",
        "Mora em qual cidade?", "Em que estado/capital o(a) Sr(a) mora?",
        "Em que bairro da cidade de (dizer o nome da cidade na qual está coletando dados), o Sr(a) mora?_Cidade"
    ],
    "FE2P10": [
        "P3", "FE2P1068", "FE2P10",
        "Para uma classificação econômica, gostaria que o(a) Sr.(a) me indicasse em qual dessas faixas está a soma da renda das pessoas que moram com o(a) Sr.(a)? (Mostrar Cartão de Renda)",
        "Considerando a soma de todos que moram na sua residência, em qual dessas faixas se enquadra a sua renda familiar mensal atual? RU e ESTIMULADA (MOSTRAR CARTÃO COM AS OPÇÕES DE RESPOSTA)",
        "Qual a sua renda familiar aproximada? (CONSIDERANDO A SOMA DE TODOS DA CASA JUNTOS)",
        "Somando todos na sua casa, em qual dessas faixas se encaixa melhor a sua renda familiar mensal? (RM e Estimulada)"
    ],
    "IC4P30": [
        "I1", "IC4P30",
        "Sobre intenção de comprar um imóvel nos próximos 2 anos, ou seja, em 24 meses, você diria que: RU e ESTIMULADA",
        "Você tem intenção de comprar um IMÓVEL ENTRE 2022 e 2024? (RU e estimulada)",
        "Você tem intenção de comprar imóvel entre Janeiro/2021 e Dezembro/2022? (RU e Estimulada)",
        "O(A) Sr.(a) tem intenção de comprar IMÓVEL nos próximos períodos (entre Abril de 2021 e Fevereiro de 2023)?",
        "ICE32P363"
    ],
    "IC4P32": [
        "I2", "IC4P32",
        "Você pensa em fechar negócio em até quantos meses? RU e estimulada",
        "Você pretende comprar este imóvel em até quanto tempo? RU e ESTIMULADA",
        "ICE32P364"
    ],
    "IC4P33_1": [
        "I3.1", "IC4P33_M1",
        "Seu interesse é por qual tipo de imóvel? RM e ESTIMULADA_M1",
        "ICE32P365_M1"
    ],
    "IC4P33_2": [
        "I3.2", "IC4P33_M2",
        "Seu interesse é por qual tipo de imóvel? RM e ESTIMULADA_M2",
        "ICE32P365_M2"
    ],
    "IC4P34_1": [
        "I4.1", "I4.1", "IC4P34_M1",
        "Seu interesse é por qual tipo de imóvel residencial para moradia? Cite até 2 por ordem de preferência. RM e ESTIMULADA_M1",
        "Que tipo de imóvel RESIDENCIAL pretende comprar? 1 (RU e Estimulada)",
        "ICE32P366_M1"
    ],
    "IC4P34_2": [
        "I4.2", "IC4P34_M2",
        "Seu interesse é por qual tipo de imóvel residencial para moradia? Cite até 2 por ordem de preferência. RM e ESTIMULADA_M2",
        "Que tipo de imóvel RESIDENCIAL pretende comprar? 2 (RU e Estimulada)",
        "ICE32P366_M2"
    ],
    "IC4P35": [
        "I5", "IC4P35",
        "Por qual destes motivos você pretende comprar este imóvel de moradia? RU e ESTIMULADA (MOSTRAR CARTÃO COM AS OPÇÕES DE RESPOSTA)",
        "Por qual motivo pretende comprar este imóvel? (RU e Estimulada)",
        "ICE32P368"
    ],
    "IC4P36": [
        "IC4P36",
        "Qual o valor do aluguel, sem incluir o valor de condomínio, que você paga atualmente? RM e ESTIMULADA",
    ],
    "IC4P37": [
        "IC4P37",
        "Nesta faixa, qual é o valor (R$)?",
    ],
    "loc1": [
        "Sobre sua intenção de alugar ou mudar de um atual imóvel alugado nos próximos 2 anos, ou seja, em 24 meses, você diria que:",
    ],
    "loc2": [
        "Você pretende locar este imóvel em até quanto tempo?",
    ],
    "loc3": [
        "Você moraria de aluguel, mesmo tendo condições de comprar um imóvel próprio? Resposta única e estimulada",
    ],
    "loc4": [
        "Por qual motivo?",
    ],
    "loc5": [
        "Por qual motivo?",
    ],
    "IIA5P37": [
        "IMD1", "IIA5P37", "Qual o valor total?",
        "Qual valor total máximo (R$) que PODERIA PAGAR por esse imóvel? RU e ESTIMULADA",
        "Qual valor o(a) Sr(a) estaria disposto a pagar por esse imóvel?",
        "Qual preço poderia pagar para um imóvel com essa metragem? ",
        "Agora vamos falar sobre as características financeiras desse imóvel de desejo. Vamos pensar no mercado atual e nas características do seu imóvel desejado: (RU e Espontânea). Qual valor o(a) Sr(a) estaria disposto a pagar por esse imóvel?"
    ],
    "IIA5P39": [
        "IMD2", "IIA5P39", "Qual o valor de entrada/ sinal seria confortável?",
        "Qual o valor de ENTRADA/SINAL seria confortável para o(a) Sr.(a)? (RU e Espontânea)",
        "Qual o valor de entrada/ sinal?",
        "Qual valor de SINAL seria confortável para o(a) Sr(a)?",
        "Qual valor máximo de sinal (entrada no ato) que PODERIA PAGAR por esse imóvel? RU e ESTIMULADA"
    ],
    "IIA5P41": [
        "IMD3", "IIA5P41", "Qual o valor de parcelas?",
        "Qual o valor de PARCELAS seria confortável?",
        "Qual valor máximo de parcela mensal que PODERIA PAGAR por esse imóvel? RU e ESTIMULADA",
        "Qual valor de PARCELA seria confortável para o(a) Sr(a)?"
    ],
    "IIA5P47": [
        "IMD4", "IIA5P47",
        "Esse imóvel teria quantos metros quadrados (m²)? RU e ESTIMULADA",
        "Qual seria o tamanho ideal (m²)?",
        "Qual seria o tamanho ideal (m²)? (Especifique)",
        "Em sua opinião, qual seria o tamanho ideal (m²) para atender as suas necessidades e de sua família? (RU e Espontânea)",
        "Agora vamos pensar nas características deste apartamento em relação ao seu tamanho e preço. Peço que para os valores, considere o mercado e suas necessidades atuais. (RU e Espontânea) Qual seria o tamanho ideal (m²)?"
    ],
    "IIA5P43": [
        "IMDR1", "IIA5P43",
        "A configuração desse imóvel teria quantos quartos? RU e ESTIMULADA",
        "Qual a quantidade de itens seria ideal em sua nova residência? RU e estimulada_Dormitórios",
        "Agora vou ler alguns cômodos e gostaria que o(a) sr. (a) dissesse quantos que seria ideal ter em sua nova residência._Quartos sem considerar suítes"
    ],
    "IIA5P44": [
        "IMDR2", "IIA5P44",
        "Desses quartos, quantos seriam do tipo suíte, ou seja, quarto com banheiro próprio integrado? RU e ESTIMULADA",
        "Qual a quantidade de itens seria ideal em sua nova residência? RU e estimulada_Suítes",
        "Agora vou ler alguns cômodos e gostaria que o(a) sr. (a) dissesse quantos que seria ideal ter em sua nova residência._Suítes"
    ],
    "IIA5P45": [
        "IMDR3", "IIA5P45",
        "E quantos banheiros no total, contando com suíte, lavabo e banheiro social? RU e ESTIMULADA",
        "Qual a quantidade de itens seria ideal em sua nova residência? RU e estimulada_Banheiros",
        "Agora vou ler alguns cômodos e gostaria que o(a) Sr.(a) dissesse quantos que seria ideal ter em sua nova residência._Banheiros Sociais (sem considerar o das suítes)"
    ],
    "IIA5P46": [
        "IMDR4", "IIA5P46", "E quantas vagas de garagem? RU e ESTIMULADA",
        "Qual a quantidade de itens seria ideal em sua nova residência? RU e estimulada_Vagas de Garagem",
        "Agora vou ler alguns cômodos e gostaria que o(a) Sr.(a) dissesse quantos que seria ideal ter em sua nova residência._Vagas de Garagem"
    ],
    "APAC9P85_1": [
        "APM98P1201_M1", "APAC9P85_M1",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique de 3 a 5 por ordem de preferência. RM e ESTIMULADA_M1",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M1",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M1",
        "Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM E ETIMULADA ? itens em rodízio_M1",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M1",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M1",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RU E ESTIMULADA (ITENS APRESENTADOS EM RODÍZIO)_M1"
    ],
    "APAC9P85_2": [
        "APM98P1201_M2", "APAC9P85_M2",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique de 3 a 5 por ordem de preferência. RM e ESTIMULADA_M2",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M2",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M2",
        "Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM E ETIMULADA ? itens em rodízio_M2",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M2",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M2",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RU E ESTIMULADA (ITENS APRESENTADOS EM RODÍZIO)_M2"
    ],
    "APAC9P85_3": [
        "APM98P1201_M3", "APAC9P85_M3",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique de 3 a 5 por ordem de preferência. RM e ESTIMULADA_M3",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M3",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M3",
        "Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM E ETIMULADA ? itens em rodízio_M3",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M3",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M3",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RU E ESTIMULADA (ITENS APRESENTADOS EM RODÍZIO)_M3"
    ],
    "APAC9P85_4": [
        "APM98P1201_M4", "APAC9P85_M4",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique de 3 a 5 por ordem de preferência. RM e ESTIMULADA_M4",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M4",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M4",
        "Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM E ETIMULADA ? itens em rodízio_M4",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M4",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M4",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RU E ESTIMULADA (ITENS APRESENTADOS EM RODÍZIO)_M4"
    ],
    "APAC9P85_5": [
        "APM98P1201_M5", "APAC9P85_M5",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique de 3 a 5 por ordem de preferência. RM e ESTIMULADA_M5",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M5",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M5",
        "Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM E ETIMULADA ? itens em rodízio_M5",
        "ÁREAS DE LAZER: apresentar book de imagens Quais as áreas que mais gostou? Indique até 5 por ordem de preferência. RM E ESTIMULADA_M5",
        "ÁREAS COMUNS - Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RM e ESTIMULADA_M5",
        "Apresentar book de imagens Quais as áreas comuns que mais gostou? Indique até 5 por ordem de preferência. RU E ESTIMULADA (ITENS APRESENTADOS EM RODÍZIO)_M5"
    ],
    "APAC9P86": [
        "APM98P1203", "APAC9P86", "APA1",
        "Em uma escala de 1 a 5, você compraria um imóvel com essas áreas comuns? RU e ESTIMULADA - ler as opções da escala",
        "Em uma escala de 1 a 5, você compraria um imóvel com essas áreas comuns? RU e ESTIMULADA (LER AS OPÇÕES DA ESCALA)",
        "Em uma escala de 1 a 5, você compraria um lote com essas áreas comuns? RU e ESTIMULADA (LER AS OPÇÕES DA ESCALA)",
        ""
    ],
    "CNM14P128": [
        "CI1",
        "CNM14P128",
        "Comprou imóvel nos últimos 12 meses? Ou seja, assinou algum contrato de compra de imóvel nos últimos 12 meses? RU e ESPONTÂNEA",
        "O(A) Sr(a) comprou algum imóvel nos últimos 12 meses?",
    ],
    "CNM14P129_1": [
        "CI2.1", "CNM14P129_M1",
        "Que tipo de imóvel comprou? RM e ESTIMULADA_M1",
        "Esse imóvel que o(a) Sr(a) comprou foi residencial, comercial ou o(a) Sr(a) comprou ambos, comercial e residencial? 1"
    ],
    "CNM14P129_2": [
        "CI2.2", "CNM14P129_M2",
        "Que tipo de imóvel comprou? RM e ESTIMULADA_M2",
        "Esse imóvel que o(a) Sr(a) comprou foi residencial, comercial ou o(a) Sr(a) comprou ambos, comercial e residencial? 2"
    ],
    "CNM14P130": [
        "CI3", "CNM14P130",
        "Que tipo de imóvel residencial comprou? RU e ESTIMULADA",
        "Que tipo de imóvel RESIDENCIAL o(a) Sr(a) comprou? (RU e Estimulada)"
    ],
    "CNM14P131": [
        "CI4.1", "CNM14P131",
        "Qual o valor do imóvel que comprou? RU e ESPONTÂNEA",
        "Qual foi o valor desse imóvel que o(a) Sr(a) comprou? (RU e Espontânea)_R$:"
    ],
    "CNM14P134": [
        "CI5.1", "CNM14P134",
        "Qual foi o motivo da compra deste imóvel? RU e ESTIMULADA",
        "Qual foi o motivo da compra deste imóvel? resposta múltipla e estimulada_M1"
    ],
    "IA15P135": [
        "IAT1", "IA15P135",
        "Em que tipo de imóvel mora atualmente? RU e ESTIMULADA",
        "Em que tipo de imóvel o Sr.(a) mora atualmente? (RU e Estimulada)"
    ],
    "IA15P136": [
        "IAT2.1", "IA15P136",
        "O seu imóvel de moradia atual está: RU e ESTIMULADA",
        "A sua residência é própria quitada, própria financiada, alugada, cedida, dos pais/ familiares ou está em outra situação? (RU E ESTIMULADA)",
        "A sua residência é: (RU e Estimulada)"
    ],
    "IA15P138": [
        "IAT3.1", "IA15P138",
        "A configuração do seu imóvel de moradia atual tem quantos quartos? RU e ESTIMULADA",
        "Qual a quantidade de itens que possui em sua residência? (RU e Espontânea)_Dormitórios",
        "Agora vou ler alguns cômodos e gostaria que o(a) Sr.(a) dissesse a quantidade que têm de cada um deles em sua residência atual? (RU e Estimulada)_Quantos dormitórios? "
    ],
    "IA15P139": [
        "IAT3.2", "IA15P139",
        "Qual a quantidade de itens possui em sua residência atual? RU e estimulada_Suítes",
        "Agora vou ler alguns cômodos e gostaria que o(a) Sr.(a) dissesse a quantidade que têm de cada um deles em sua residência atual? (RU e Estimulada)_Quantas suítes?"
    ],
    "IA15P140": [
        "IAT3.3", "IA15P140",
        "Qual a quantidade de itens que possui em sua residência? (RU e Espontânea)_Banheiros",
        "gora vou ler alguns cômodos e gostaria que o(a) Sr.(a) dissesse a quantidade que têm de cada um deles em sua residência atual? (RU e Estimulada)_Quantos banheiros?"
    ],
    "IA15P141": [
        "IAT3.4", "IA15P141",
        "Qual a quantidade de itens que possui em sua residência? (RU e Espontânea)_Vagas de Garagem",
        "Agora vou ler alguns cômodos e gostaria que o(a) Sr.(a) dissesse a quantidade que têm de cada um deles em sua residência atual? (RU e Estimulada)_Quantas vagas de garagem?"
    ],
    "PS3P17": [
        "P6.1", "PS3P17",
        "Qual é o seu nível de escolaridade? RU e ESPONTÂNEA",
        "Até que ano o(a) sr. (a) estudou? (RU e Espontânea)",
        "Qual a sua escolaridade? (RU e Espontânea)"
    ],
    "PS3P19": [
        "P7.1", "PS3P19", "Qual o seu estado civil?",
        "Qual o seu estado civil? (RU e Espontânea)",
        "Qual é o seu estado civil? RU e ESTIMULADA ORIENTAÇÃO: Se responder SOLTEIRO confirmar se realmente não mora com um(a) parceiro(a)"
    ],
    "PS3P19_det": [
        "O(A) Sr(a) me disse que é solteiro(a), mas gostaria de saber se o(a) Sr(a) mora com alguém em condição de união estável? (RU e Espontânea)"
    ],
    "PS3P23": [
        "P8.1", "PS3P23",
        "Incluindo você, quantas pessoas moram em sua residência? RU e ESPONTÂNEA",
        "Contando com o(a) Sr(a), quantas pessoas, moram na sua residência? (RU e Espontânea)",
        "Gostaria que o(a) Sr(a) dissesse quantas pessoas moram na sua casa, incluindo o(a) Sr.(a)? (RU e Espontânea)"
    ],
    "PS3P25": [
        "P9", "PS3P25",
        "Qual é a sua principal ocupação profissional atualmente?",
        "Atualmente o(a) Sr(a) exerce a sua profissão de que forma? (RU e Estimulada)",
        "Atualmente de que forma o(a) Sr(a) exerce a sua profissão? (RU e Estimulada)"
    ],
    "Data": ["Data"],
    "Estado": ["Estado"],
    "Cidade": ["Cidade"],
    "Status": ["Status"],
    "Latitude": ["Latitude"],
    "Longitude": ["Longitude"]
}

# Adicione este dicionário em src/data_processing.py

CODIGOS_PARA_TEXTO_ORIGINAL = {
    "Código": "Código",
    "FE2P3": "2 - Gênero: (SOMENTE REGISTRAR)",
    "FE2P5": "4 - Qual é a sua idade?",
    "FE2P6": "5 - Faixa etária: (SOMENTE REGISTRAR)",
    "FE2P10":
    "9 - Considerando a soma de todos que moram na sua residência, em qual dessas faixas se enquadra a sua renda familiar mensal atual? RU e ESTIMULADA (MOSTRAR CARTÃO COM AS OPÇÕES DE RESPOSTA)",
    "FE2P7": "Cidade de moradia",
    "PS3P17": "14 - Qual é o seu nível de escolaridade? RU e ESPONTÂNEA",
    "PS3P19":
    "16 - Qual é o seu estado civil? RU e ESTIMULADA ORIENTAÇÃO: Se responder SOLTEIRO confirmar se realmente não mora com um(a) parceiro(a)",
    "PS3P20": "18 - Você tem quantos filhos? RU e ESPONTÂNEA",
    "PS3P23":
    "19 - Incluindo você, quantas pessoas moram em sua residência? RU e ESPONTÂNEA",
    "PS3P25":
    "20 - Qual é a sua principal ocupação profissional atualmente? RU e ESTIMULADA (MOSTRAR CARTÃO COM AS OPÇÕES DE RESPOSTA)",
    "IC4P30":
    "26 - Sobre intenção de comprar um imóvel nos próximos 2 anos, ou seja, em 24 meses, você diria que: RU e ESTIMULADA",
    "IC4P31":
    "27 - Por qual motivo não tem intenção de comprar um imóvel nos próximos 2 anos? RU e ESPONTÂNEA ORIENTAÇÃO: NÃO apresentar as alternativas",
    "IC4P32":
    "28 - Você pretende comprar este imóvel em até quanto tempo? RU e ESTIMULADA",
    "IC4P33_1":
    "29 - Seu interesse é por qual tipo de imóvel? RM e ESTIMULADA_M1",
    "IC4P33_2":
    "29 - Seu interesse é por qual tipo de imóvel? RM e ESTIMULADA_M2",
    "IC4P33_3":
    "29 - Seu interesse é por qual tipo de imóvel? RM e ESTIMULADA_M3",
    "IC4P34_1":
    "30 - Seu interesse é por qual tipo de imóvel residencial para moradia? Cite até 2 por ordem de preferência. RM e ESTIMULADA_M1",
    "IC4P34_2":
    "30 - Seu interesse é por qual tipo de imóvel residencial para moradia? Cite até 2 por ordem de preferência. RM e ESTIMULADA_M2",
    "IC4P35":
    "31 - Por qual destes motivos você pretende comprar este imóvel de moradia? RU e ESTIMULADA (MOSTRAR CARTÃO COM AS OPÇÕES DE RESPOSTA)",
    "IC4P36":
    "34 - Qual o valor do aluguel, sem incluir o valor de condomínio, que você paga atualmente? RM e ESTIMULADA",
    "IC4P37": "35 - Nesta faixa, qual é o valor (R$)?",
    "loc1":
    "36 - Sobre sua intenção de alugar ou mudar de um atual imóvel alugado nos próximos 2 anos, ou seja, em 24 meses, você diria que: RU e ESTIMULADA",
    "loc2":
    "37 - Você pretende locar este imóvel em até quanto tempo? RU e ESTIMULADA",
    "loc3":
    "38 - Você moraria de aluguel, mesmo tendo condições de comprar um imóvel próprio? RU e ESTIMULADA",
    "loc4": "39 - Por qual motivo? RU e ESTIMULADA",
    "loc5": "40 - Por qual motivo? RU e ESTIMULADA",
    "CNM14P128":
    "64 - Comprou imóvel nos últimos 12 meses? Ou seja, assinou algum contrato de compra de imóvel nos últimos 12 meses? RU e ESPONTÂNEA",
    "CNM14P129_1": "65 - Que tipo de imóvel comprou? RM e ESTIMULADA_M1",
    "CNM14P129_2": "65 - Que tipo de imóvel comprou? RM e ESTIMULADA_M2",
    "CNM14P130":
    "66 - Que tipo de imóvel residencial comprou? RU e ESTIMULADA",
    "CNM14P131": "67 - Qual o valor do imóvel que comprou? RU e ESPONTÂNEA",
    "CNM14P132": "85 - E qual o valor de entrada que pagou? RU e ESPONTÂNEA",
    "CNM14P133": "87 - E o valor da parcela que está pagando? RU e ESPONTÂNEA",
    "CNM14P134":
    "89 - Qual foi o motivo da compra deste imóvel? RU e ESTIMULADA",
    "IA15P135": "90 - Em que tipo de imóvel mora atualmente? RU e ESTIMULADA",
    "IA15P136": "91 - O seu imóvel de moradia atual está: RU e ESTIMULADA",
    "IA15P137": "92 - Quitado ou financiado? RU e ESTIMULADA",
    "IA15P138":
    "93 - A configuração do seu imóvel de moradia atual tem quantos quartos? RU e ESTIMULADA",
    "IA15P139":
    "94 - Desses quartos, quantos seriam do tipo suíte, ou seja, quarto com banheiro próprio integrado? RU e ESTIMULADA",
    "IA15P140":
    "95 - E quantos banheiros no total, contando com suíte, lavabo e banheiro social? RU e ESTIMULADA",
    "IA15P141": "96 - E quantas vagas de garagem? RU e ESTIMULADA",
    "Cidade": "Cidade",
    "Estado": "Estado",
    "Status": "Status",
    "Geração": "Geração",
    "Capital": "Capital",
    "ESTADO": "Estado",
    "REGIAO": "Região",
    "RENDA": "Renda arredondada",
    "Intencao": "Intenção",
    "Data": "Data Pesquisa",
    "Latitude": "Latitude",
    "Longitude": "Longitude"
}


def map_api_columns_to_target_codes(records: list) -> tuple[list, set]:
    """
    Mapeia os nomes das colunas (chaves) dos registros brutos de API para os códigos alvo padronizados.
    Usa SOMENTE correspondência exata. A similaridade semântica foi desativada.
    Não exibe mensagens no Streamlit diretamente.

    Args:
        records (list): Uma lista de dicionários, onde cada dicionário é um registro de respondente bruto.
                        As chaves são os nomes das colunas da API.

    Returns:
        tuple: Uma tupla contendo:
               - list: Nova lista de dicionários com chaves mapeadas.
               - set: Um conjunto de códigos alvo que foram mapeados com sucesso (ex: {'Código', 'FE2P3'}).
    """
    if not records:
        return [], set()

    exact_match_map = {}
    for code, texts in perguntas_alvo_codigos.items():
        for text in texts:
            clean_text = text.strip().lower()
            if clean_text:
                exact_match_map[clean_text] = code

    processed_records = []
    unique_mapped_codes = set(
    )  # Para armazenar os códigos alvo que foram efetivamente mapeados

    original_columns = list(records[0].keys())
    column_name_map = {}

    for original_col in original_columns:
        mapped_key = original_col  # Inicia com o nome original

        if original_col is None:
            column_name_map[original_col] = None
            continue

        normalized_original_col = original_col.strip()
        if not normalized_original_col:
            column_name_map[original_col] = ''
            continue

        normalized_original_col_lower = normalized_original_col.lower()

        # 1. Tentar correspondência exata com o código alvo (a chave no dicionário)
        if normalized_original_col in perguntas_alvo_codigos:
            mapped_key = normalized_original_col
            unique_mapped_codes.add(mapped_key)
        # 2. Tentar correspondência exata com os textos alvo (valores no dicionário)
        elif normalized_original_col_lower in exact_match_map:
            mapped_key = exact_match_map[normalized_original_col_lower]
            unique_mapped_codes.add(mapped_key)
        # Se não encontrou correspondência exata, mapped_key permanece original_col

        column_name_map[original_col] = mapped_key

    # Aplicar o mapeamento a todos os registros
    for record in records:
        new_record = {}
        for original_key, value in record.items():
            mapped_key = column_name_map.get(original_key, original_key)
            new_record[mapped_key] = value
        processed_records.append(new_record)

    return processed_records, unique_mapped_codes


# --- 1. LÓGICA DE IDADE ---


def categorize_generation(age):
    """Categoriza a geração com base na idade numérica."""
    try:
        age = int(age)
        if age >= 79: return '6. Geração Silenciosa'
        elif age >= 60: return '5. Baby Boomers'
        elif age >= 44: return '4. Geração X'
        elif age >= 28: return '3. Geração Y'
        elif age >= 12: return '2. Geração Z'
        else: return '1. Geração Alfa'
    except (ValueError, TypeError):
        return None


def reclassificar_idade(age):
    """Reclassifica a idade numérica em faixas etárias."""
    try:
        age = int(age)
        if age < 25: return '1. Menos de 25'
        elif 25 <= age <= 34: return '2. De 25 a 34 anos'
        elif 35 <= age <= 44: return '3. De 35 a 44 anos'
        elif 45 <= age <= 54: return '4. De 45 a 54 anos'
        elif 55 <= age <= 64: return '5. De 55 a 64 anos'
        elif 65 <= age <= 74: return '6. De 65 a 74 anos'
        else: return '7. Acima de 75'
    except (ValueError, TypeError):
        return None


# --- 2. LÓGICA DE RENDA ---
@st.cache_data
def load_classification_rules():
    """Carrega as regras de classificação de renda do arquivo JSON."""
    try:
        rule_path = Path(
            __file__
        ).parent.parent / "config" / "regras_classificacao_renda.json"
        with open(rule_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(
            "Arquivo de regras 'config/regras_classificacao_renda.json' não encontrado."
        )
        return None


def classify_income_by_rules(valor, data_criacao_pesquisa, all_rules):
    """Classifica a renda e retorna uma tupla: (classe_agregada, classe_detalhada)"""
    if pd.isna(valor) or pd.isna(data_criacao_pesquisa) or all_rules is None:
        return (None, None)
    if isinstance(data_criacao_pesquisa, str):
        data_criacao_pesquisa = datetime.strptime(data_criacao_pesquisa,
                                                  '%Y-%m-%d').date()
    elif isinstance(data_criacao_pesquisa, pd.Timestamp) or isinstance(
            data_criacao_pesquisa, datetime):
        data_criacao_pesquisa = data_criacao_pesquisa.date()
    regras_aplicaveis = None
    for versao in all_rules.get('versoes', []):
        data_inicio = datetime.strptime(
            versao.get('data_inicio_validade', '1900-01-01'),
            '%Y-%m-%d').date()
        data_fim = datetime.strptime(
            versao.get('data_fim_validade', '2999-12-31'), '%Y-%m-%d').date()
        if data_inicio <= data_criacao_pesquisa <= data_fim:
            regras_aplicaveis = versao['regras']
            break
    if not regras_aplicaveis:
        return ("Versão de Regra Incompatível", "Versão de Regra Incompatível")
    for regra in regras_aplicaveis:
        if regra['min_renda'] <= valor <= regra['max_renda']:
            return (regra['classe_agregada'], regra['classe_detalhada'])
    return ("Não Classificado", "Não Classificado")


def calcular_media_faixa(faixa: str) -> int | None:
    """Calcula o valor numérico médio de uma faixa de renda textual."""
    if not isinstance(faixa, str): return None
    numeros_encontrados = re.findall(r'[\d\.,]+', faixa)
    if not numeros_encontrados: return None
    numeros_convertidos = []
    for num_str in numeros_encontrados:
        try:
            num_limpo = num_str.replace('.', '').replace(',', '.')
            numeros_convertidos.append(float(num_limpo))
        except ValueError:
            continue
    numeros_filtrados = [n for n in numeros_convertidos if n >= 1000]
    if not numeros_filtrados: return None
    return int(np.mean(numeros_filtrados))


def classificar_faixa_antiga(valor: int | None) -> str | None:
    """Usa o valor estimado para classificar em uma faixa de renda padronizada (legado)."""
    if valor is None: return None
    if valor <= 1500: return "01. Até R$ 1,5 mil"
    if 1500 < valor <= 2500: return "02. De R$ 1,5 mil a R$ 2,5 mil"
    if 2500 < valor <= 4500: return "03. De R$ 2,5 mil a R$ 4,5 mil"
    if 4500 < valor <= 5500: return "04. De R$ 4,5 mil a R$ 5,5 mil"
    if 5500 < valor <= 8000: return "05. De R$ 5,5 mil a R$ 8 mil"
    if 8000 < valor <= 11000: return "06. De R$ 8 mil a R$ 11 mil"
    if 11000 < valor <= 13000: return "07. De R$ 11 mil a R$ 13 mil"
    if 13000 < valor <= 16000: return "08. De R$ 13 mil a R$ 16 mil"
    if 16000 < valor <= 18500: return "09. De R$ 16 mil a R$ 18,5 mil"
    if 18500 < valor <= 21000: return "10. De R$ 18,5 mil a R$ 21 mil"
    if 21000 < valor <= 24500: return "11. De R$ 21 mil a R$ 24,5 mil"
    if 24500 < valor <= 28000: return "12. De R$ 24,5 mil a R$ 28 mil"
    return "13. Acima de R$ 28 mil"


def map_renda_to_macro_faixa(faixa_padronizada: str) -> str | None:
    """Converte a faixa de renda padronizada para uma macro categoria (legado)."""
    MAPA_RENDA_MACRO = {
        "01. Até R$ 1,5 mil": "1. Menor que R$ 2,5 mil",
        "02. De R$ 1,5 mil a R$ 2,5 mil": "1. Menor que R$ 2,5 mil",
        "03. De R$ 2,5 mil a R$ 4,5 mil": "2. R$ 2,5 a R$ 5 mil",
        "04. De R$ 4,5 mil a R$ 5,5 mil": "2. R$ 2,5 a R$ 5 mil",
        "05. De R$ 5,5 mil a R$ 8 mil": "3. R$ 5 a R$ 10 mil",
        "06. De R$ 8 mil a R$ 11 mil": "3. R$ 5 a R$ 10 mil",
        "07. De R$ 11 mil a R$ 13 mil": "4. R$ 10 a R$ 20 mil",
        "08. De R$ 13 mil a R$ 16 mil": "4. R$ 10 a R$ 20 mil",
        "09. De R$ 16 mil a R$ 18,5 mil": "4. R$ 10 a R$ 20 mil",
        "10. De R$ 18,5 mil a R$ 21 mil": "4. R$ 10 a R$ 20 mil",
        "11. De R$ 21 mil a R$ 24,5 mil": "5. Acima de R$ 20 mil",
        "12. De R$ 24,5 mil a R$ 28 mil": "5. Acima de R$ 20 mil",
        "13. Acima de R$ 28 mil": "5. Acima de R$ 20 mil"
    }
    if not isinstance(faixa_padronizada, str): return None
    return MAPA_RENDA_MACRO.get(faixa_padronizada)


# --- 3. LÓGICA DE LOCALIZAÇÃO ---

MAPA_ESTADO_REGIAO = {
    'AC': 'Norte',
    'AP': 'Norte',
    'AM': 'Norte',
    'PA': 'Norte',
    'RO': 'Norte',
    'RR': 'Norte',
    'TO': 'Norte',
    'AL': 'Nordeste',
    'BA': 'Nordeste',
    'CE': 'Nordeste',
    'MA': 'Nordeste',
    'PB': 'Nordeste',
    'PE': 'Nordeste',
    'PI': 'Nordeste',
    'RN': 'Nordeste',
    'SE': 'Nordeste',
    'DF': 'Centro-Oeste',
    'GO': 'Centro-Oeste',
    'MT': 'Centro-Oeste',
    'MS': 'Centro-Oeste',
    'ES': 'Sudeste',
    'MG': 'Sudeste',
    'RJ': 'Sudeste',
    'SP': 'Sudeste',
    'PR': 'Sul',
    'RS': 'Sul',
    'SC': 'Sul'
}
LISTA_CAPITAIS = [
    'ARACAJU', 'BELEM', 'BELO HORIZONTE', 'BOA VISTA', 'BRASILIA',
    'CAMPO GRANDE', 'CUIABA', 'CURITIBA', 'FLORIANOPOLIS', 'FORTALEZA',
    'GOIANIA', 'JOAO PESSOA', 'MACAPA', 'MACEIO', 'MANAUS', 'NATAL', 'PALMAS',
    'PORTO ALEGRE', 'PORTO VELHO', 'RECIFE', 'RIO BRANCO', 'RIO DE JANEIRO',
    'SALVADOR', 'SAO LUIS', 'SAO PAULO', 'TERESINA', 'VITORIA'
]


def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    # Primeiro, remove o sufixo " - UF" se ele existir
    # A função split(' - ')[0] pega apenas a parte do texto antes do delimitador.
    texto_sem_uf = texto.split(' - ')[0]

    # O resto da lógica de limpeza agora é aplicado ao texto já fatiado
    return ''.join(c for c in unicodedata.normalize('NFD', texto_sem_uf)
                   if unicodedata.category(c) != 'Mn').upper().strip()


def map_estado_to_regiao(estado):
    if not isinstance(estado, str): return None
    return MAPA_ESTADO_REGIAO.get(estado.strip().upper())


def classify_cidade(cidade):
    cidade_normalizada = normalizar_texto(cidade)
    if cidade_normalizada in LISTA_CAPITAIS: return 'Capital'
    elif cidade_normalizada: return 'Interior'
    return None


# --- 4. LÓGICA DE INTENÇÃO DE COMPRA ---

MAPA_INTENCAO_COMPRA = {
    "1. Você não pretende comprar imóvel neste período":
    "Não pretende comprar",
    "1. Você não pretende locar imóvel neste período":
    "Não pretende comprar",  # Assumindo que o objetivo é unificar
    "1. Não pretendo comprar imóvel neste período":
    "Não pretende comprar",
    "3. Pretende comprar e já está procurando na internet":
    "Pretende e procurando",
    "4. Pretende comprar e já começou a visitar imobiliárias, stands de vendas e imóveis":
    "Pretende e visitando",
    "4. Pretende locar e já começou a visitar imobiliárias e imóveis":
    "Pretende e visitando",
    "2. Pretende comprar, mas ainda não começou a procurar":
    "Pretende, mas não procurando",
    "3. Pretende locar e já está procurando na internet":
    "Pretende e procurando",
    "2. Pretende locar, mas ainda não começou a procurar":
    "Pretende, mas não procurando",
    "2. Sim, pretendo comprar um imóvel neste período":
    "Pretende, mas não procurando"
}

MAPA_TEMPO_INTENCAO = {
    # Variações para "Até 6 meses"
    '1. Em até 6 meses': '1. Até 6 meses',
    'Em até 6 meses': '1. Até 6 meses',
    '1. Em até 3 meses': '1. Até 6 meses',  # Agrupado em "Até 6 meses"
    '2. Em até 6 meses': '1. Até 6 meses',

    # Variações para "Até 1 ano"
    '2. Em até 12 meses': '2. Até 1 ano',
    '3. Em até 12 meses': '2. Até 1 ano',
    'Em até 12 meses': '2. Até 1 ano',
    '2. Em até 1 ano': '2. Até 1 ano',
    '2. Em até 12 meses (1 ano)': '2. Até 1 ano',

    # Variações para "Até 1 ano e meio"
    '3. Em até 18 meses': '3. Até 1 ano e meio',
    'Em até 18 meses': '3. Até 1 ano e meio',
    '3. Em até 18 meses (1 ano e meio)': '3. Até 1 ano e meio',

    # Variações para "Até 2 anos"
    '4. Em até 24 meses': '4. Até 2 anos',
    'Em até 24 meses': '4. Até 2 anos',
    '4. Em até 24 meses (2 anos)': '4. Até 2 anos',

    # Variações para "Mais de 2 anos"
    '5. Acima de 12 meses':
    '5. Mais de 2 anos',  # Assume que 'Acima de 12' já entra na categoria mais longa
    '5. Acima de 24 meses': '5. Mais de 2 anos',
    'Acima de 24 meses': '5. Mais de 2 anos',
    '5. Acima de 2 anos': '5. Mais de 2 anos',
    '5. Acima de 24 meses (acima de 2 anos)': '5. Mais de 2 anos',

    # Valores a serem ignorados
    '-': None
}


def padronizar_resposta(resposta, mapa):
    """
    Busca um valor em um dicionário de mapeamento.
    Se não encontrar, retorna None (lógica coringa).
    """
    if not isinstance(resposta, str):
        return None
    # A mudança chave está aqui: o segundo argumento de .get() agora é None.
    return mapa.get(resposta, None)


def impute_missing_states(df: pd.DataFrame) -> pd.DataFrame:
    """
    Imputa valores de estado faltantes ('-' ou Nulos) usando o valor mais frequente (moda)
    do estado dentro do mesmo grupo de pesquisa (survey_id).
    Cria uma nova coluna 'Estado_corrigido' com os dados limpos.
    """
    # Garante que a coluna 'Estado' exista no dataframe
    if 'Estado' not in df.columns:
        # Se não houver coluna de estado, cria uma coluna corrigida vazia para evitar erros
        df['Estado_corrigido'] = pd.NA
        return df

    # Substitui o hífen por um valor Nulo padrão (NaN) para facilitar o uso das funções do Pandas
    df['Estado_temp'] = df['Estado'].replace('-', pd.NA)

    # Calcula a moda (estado mais frequente) para cada grupo de 'survey_id'
    # 'transform' aplica o resultado de volta a todas as linhas do grupo original.
    df['estado_imputado'] = df.groupby('survey_id')['Estado_temp'].transform(
        lambda x: x.mode()[0] if not x.mode().empty else pd.NA)

    # Cria a nova coluna 'Estado_corrigido' preenchendo os nulos com o valor imputado
    df['Estado_corrigido'] = df['Estado_temp'].fillna(df['estado_imputado'])

    # Remove as colunas temporárias
    df.drop(columns=['Estado_temp', 'estado_imputado'], inplace=True)

    return df


# --- FUNÇÃO ORQUESTRADORA ---
def process_and_standardize_data(long_df: pd.DataFrame,
                                 surveys_df: pd.DataFrame) -> pd.DataFrame:
    if long_df.empty:
        return pd.DataFrame()

    regras_de_renda = load_classification_rules()
    if regras_de_renda is None:
        return pd.DataFrame()

    # 1. Pivotar e Enriquecer com Metadados da Pesquisa
    wide_df = long_df.pivot_table(index=['respondent_id', 'survey_id'],
                                  columns='question_code',
                                  values='answer_value',
                                  aggfunc='first').reset_index()
    wide_df = wide_df.merge(
        surveys_df[['survey_id', 'research_name', 'creation_date']],
        on='survey_id',
        how='left')

    required_cols = [
        'Data', 'FE2P5', 'FE2P10', 'FE2P7', 'Estado', 'IC4P30', 'IC4P32',
        'FE2P3', 'Latitude', 'Longitude'
    ]
    for col in required_cols:
        if col not in wide_df.columns:
            wide_df[col] = None

    # 2. Transformações e Validações de Dados
    wide_df['data_pesquisa'] = pd.to_datetime(wide_df['Data'],
                                              errors='coerce',
                                              dayfirst=True)
    hoje = pd.to_datetime('today').normalize()
    future_dates_mask = wide_df['data_pesquisa'] > hoje
    if future_dates_mask.any():
        wide_df.loc[future_dates_mask, 'data_pesquisa'] = pd.NaT
    wide_df['data_pesquisa'] = wide_df['data_pesquisa'].dt.date

    wide_df = impute_missing_states(wide_df)

    # 3. Geração de Novas Colunas
    wide_df['genero'] = wide_df['FE2P3']
    wide_df['latitude'] = pd.to_numeric(wide_df['Latitude'], errors='coerce')
    wide_df['longitude'] = pd.to_numeric(wide_df['Longitude'], errors='coerce')
    wide_df['estado_nome'] = wide_df['Estado_corrigido'].apply(
        map_uf_to_estado_nome)
    wide_df['regiao'] = wide_df['Estado_corrigido'].apply(map_estado_to_regiao)
    wide_df['localidade'] = wide_df['FE2P7'].apply(classify_cidade)
    wide_df['idade_numerica'] = pd.to_numeric(wide_df['FE2P5'],
                                              errors='coerce')
    wide_df['geracao'] = wide_df['idade_numerica'].apply(categorize_generation)
    wide_df['faixa_etaria'] = wide_df['idade_numerica'].apply(
        reclassificar_idade)
    wide_df['intencao_compra_padronizada'] = wide_df['IC4P30'].apply(
        lambda x: padronizar_resposta(x, MAPA_INTENCAO_COMPRA))
    wide_df['tempo_intencao_padronizado'] = wide_df['IC4P32'].apply(
        lambda x: padronizar_resposta(x, MAPA_TEMPO_INTENCAO))
    wide_df['renda_valor_estimado'] = wide_df['FE2P10'].apply(
        calcular_media_faixa)
    wide_df['renda_faixa_padronizada'] = wide_df['renda_valor_estimado'].apply(
        classificar_faixa_antiga)
    wide_df['renda_macro_faixa'] = wide_df['renda_faixa_padronizada'].apply(
        map_renda_to_macro_faixa)

    # Aplica a nova função de classificação que retorna uma tupla
    resultados_renda = wide_df.apply(lambda row: classify_income_by_rules(
        row['renda_valor_estimado'], row['creation_date'], regras_de_renda),
                                     axis=1)
    wide_df[['renda_classe_agregada', 'renda_classe_detalhada'
             ]] = pd.DataFrame(resultados_renda.tolist(), index=wide_df.index)

    # 4. Selecionar e Renomear Colunas para a Tabela Final
    final_cols_map = {
        'respondent_id': 'respondent_id',
        'survey_id': 'survey_id',
        'research_name': 'research_name',
        'data_pesquisa': 'data_pesquisa',
        'idade_original': 'FE2P5',
        'idade_numerica': 'idade_numerica',
        'geracao': 'geracao',
        'faixa_etaria': 'faixa_etaria',
        'renda_texto_original': 'FE2P10',
        'renda_valor_estimado': 'renda_valor_estimado',
        'renda_faixa_padronizada': 'renda_faixa_padronizada',
        'renda_macro_faixa': 'renda_macro_faixa',
        'renda_classe_agregada': 'renda_classe_agregada',
        'renda_classe_detalhada': 'renda_classe_detalhada',
        'cidade_original': 'FE2P7',
        'localidade': 'localidade',
        'estado_original': 'Estado',
        'estado_nome': 'estado_nome',
        'regiao': 'regiao',
        'intencao_compra_original': 'IC4P30',
        'intencao_compra_padronizada': 'intencao_compra_padronizada',
        'tempo_intencao_original': 'IC4P32',
        'tempo_intencao_padronizado': 'tempo_intencao_padronizado',
        'genero': 'genero',
        'latitude': 'latitude',
        'longitude': 'longitude'
    }

    analytics_df = pd.DataFrame()
    for new_col, original_col in final_cols_map.items():
        if original_col in wide_df.columns:
            analytics_df[new_col] = wide_df[original_col]
        else:
            analytics_df[new_col] = None

    return analytics_df


# Adicione este bloco em src/data_processing.py

MAPA_UF_NOME = {
    'AC': 'Acre',
    'AL': 'Alagoas',
    'AP': 'Amapá',
    'AM': 'Amazonas',
    'BA': 'Bahia',
    'CE': 'Ceará',
    'DF': 'Distrito Federal',
    'ES': 'Espírito Santo',
    'GO': 'Goiás',
    'MA': 'Maranhão',
    'MT': 'Mato Grosso',
    'MS': 'Mato Grosso do Sul',
    'MG': 'Minas Gerais',
    'PA': 'Pará',
    'PB': 'Paraíba',
    'PR': 'Paraná',
    'PE': 'Pernambuco',
    'PI': 'Piauí',
    'RJ': 'Rio de Janeiro',
    'RN': 'Rio Grande do Norte',
    'RS': 'Rio Grande do Sul',
    'RO': 'Rondônia',
    'RR': 'Roraima',
    'SC': 'Santa Catarina',
    'SP': 'São Paulo',
    'SE': 'Sergipe',
    'TO': 'Tocantins'
}


def map_uf_to_estado_nome(uf_sigla):
    """Converte a sigla do estado para seu nome completo."""
    if not isinstance(uf_sigla, str):
        return None
    return MAPA_UF_NOME.get(uf_sigla.strip().upper())


# Dicionário para mapear as faixas detalhadas para as macro categorias
MAPA_RENDA_MACRO = {
    "01. Até R$ 1,5 mil": "1. Menor que R$ 2,5 mil",
    "02. De R$ 1,5 mil a R$ 2,5 mil": "1. Menor que R$ 2,5 mil",
    "03. De R$ 2,5 mil a R$ 4,5 mil": "2. R$ 2,5 a R$ 5 mil",
    "04. De R$ 4,5 mil a R$ 5,5 mil": "2. R$ 2,5 a R$ 5 mil",
    "05. De R$ 5,5 mil a R$ 8 mil": "3. R$ 5 a R$ 10 mil",
    "06. De R$ 8 mil a R$ 11 mil": "3. R$ 5 a R$ 10 mil",
    "07. De R$ 11 mil a R$ 13 mil": "4. R$ 10 a R$ 20 mil",
    "08. De R$ 13 mil a R$ 16 mil": "4. R$ 10 a R$ 20 mil",
    "09. De R$ 16 mil a R$ 18,5 mil": "4. R$ 10 a R$ 20 mil",
    "10. De R$ 18,5 mil a R$ 21 mil": "4. R$ 10 a R$ 20 mil",
    "11. De R$ 21 mil a R$ 24,5 mil": "5. Acima de R$ 20 mil",
    "12. De R$ 24,5 mil a R$ 28 mil": "5. Acima de R$ 20 mil",
    "13. Acima de R$ 28 mil": "5. Acima de R$ 20 mil"
}
