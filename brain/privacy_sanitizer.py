import re

class PrivacySanitizer:
    """
    Ensures no PII (Personally Identifiable Information) or sensitive data
    is stored, exposed, or logged across the BRAIN pipeline.
    """
    
    CPF_PATTERN = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
    RG_PATTERN = re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}-?[\dXxbB]\b')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[-\s]?\d{4}\b')
    
    @classmethod
    def mask_cpf(cls, text: str) -> str:
        def replace_cpf(match):
            val = match.group(0)
            digits = re.sub(r'\D', '', val)
            if len(digits) == 11:
                return f"{digits[:3]}.***.***-{digits[-2:]}"
            return "[CPF MASKED]"
        return cls.CPF_PATTERN.sub(replace_cpf, text)

    @classmethod
    def mask_rg(cls, text: str) -> str:
        return cls.RG_PATTERN.sub("[RG MASKED]", text)

    @classmethod
    def mask_email(cls, text: str) -> str:
        def replace_email(match):
            email = match.group(0)
            parts = email.split('@')
            if len(parts) == 2:
                name = parts[0]
                masked_name = name[0] + "***" if len(name) > 1 else "*"
                return f"{masked_name}@{parts[1]}"
            return "[EMAIL MASKED]"
        return cls.EMAIL_PATTERN.sub(replace_email, text)

    @classmethod
    def mask_phone(cls, text: str) -> str:
        return cls.PHONE_PATTERN.sub("[TELEFONE MASKED]", text)

    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        Applies full sanitization suite to text.
        """
        if not text or not isinstance(text, str):
            return text
        
        sanitized = text
        sanitized = cls.mask_cpf(sanitized)
        sanitized = cls.mask_rg(sanitized)
        sanitized = cls.mask_email(sanitized)
        sanitized = cls.mask_phone(sanitized)
        return sanitized

    @classmethod
    def contains_pii(cls, text: str) -> bool:
        if not text or not isinstance(text, str):
            return False
        return bool(
            cls.CPF_PATTERN.search(text) or
            cls.EMAIL_PATTERN.search(text) or
            cls.PHONE_PATTERN.search(text)
        )
