import re

rg_re = re.compile(
    r"(?i)\brg\s*[:\-]?\s*\d{1,2}\.?\d{3}\.?\d{3}-?[\dxX]?\b"  # Keyword RG explicitly
    r"|\b[a-z]{2}\s*-\s*\d{1,2}\.?\d{3}\.?\d{3}-?[\dxX]?\b"      # State code explicitly (MG-12.345.678)
    r"|\b\d{1,2}\.\d{3}\.\d{3}\s+ssp\s+[a-z]{2}\b"               # SSP [State] explicitly
    r"|\b\d{1,2}\.\d{3}\.?\d{3}-[\dxX]\b"                       # Formato rigoroso com ponto e verificador
)

test_strings = [
    "meu rg 12345678",
    "numero 12345678",
    "cep 12345678",
    "rg: 12.345.678 SSP MG",
    "MG-12.345.678",
    "12.345.678"
]

for s in test_strings:
    print(f"{s}: {rg_re.findall(s)}")
