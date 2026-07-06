#!/usr/bin/env python3
"""Mock generator for LGPD-safe development data."""
import random
import string

def fake_cpf():
    return f"{random.randint(100,999)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(10,99)}"

def fake_rg():
    return f"{random.randint(10,99)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(0,9)}"

def fake_name():
    first = ['Joao', 'Maria', 'Pedro', 'Ana', 'Carlos', 'Julia', 'Rafael', 'Beatriz']
    last = ['Silva', 'Santos', 'Oliveira', 'Souza', 'Lima', 'Pereira', 'Ferreira', 'Almeida']
    return f"{random.choice(first)} {random.choice(last)}"

def fake_cartorio():
    return f"{random.choice(['1o', '2o', '3o'])} Tabelionato de Notas de {random.choice(['Uberlandia', 'Sao Paulo', 'Rio'])}"

if __name__ == "__main__":
    print(f"CPF: {fake_cpf()}")
    print(f"RG:  {fake_rg()}")
    print(f"Name: {fake_name()}")
    print(f"Cartorio: {fake_cartorio()}")
