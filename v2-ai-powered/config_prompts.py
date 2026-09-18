"""
config_prompts.py

Prompts estructurados para extracción de datos de facturas con Claude.
Diseñados para garantizar output en JSON con estructura predecible.
"""

INVOICE_EXTRACTION_PROMPT = """You are an invoice data extraction expert. Your task is to extract key information from the provided invoice document (whether scanned PDF text, image description, or structured data).

CRITICAL: You MUST respond ONLY with valid JSON, nothing else. No preamble, no explanation, no markdown code blocks — just the JSON object.

Extract the following fields:
- invoice_date: fecha de la factura (formato YYYY-MM-DD)
- invoice_number: número de comprobante
- invoice_type: tipo (FACTURA, NOTA DE CREDITO, NOTA DE DEBITO, etc.)
- point_of_sale: punto de venta (número)
- customer_name: nombre del cliente
- customer_tax_id: CUIT/DNI del cliente
- currency: moneda (ARS, USD, etc.)
- exchange_rate: tipo de cambio (si aplica)
- line_items: array de items con {description, quantity, unit_price, net_amount, tax_amount, total}
- net_total: monto neto total
- tax_total: monto impuesto total (IVA u otro)
- total_amount: monto total
- authorization_code: código de autorización (CAE, si está disponible)
- notes: notas o observaciones (si las hay)

If a field is not found or unclear, use null.
Quantities and amounts must be numbers, not strings.

Invoice text/data:
{invoice_text}

Respond ONLY with the JSON object, no other text."""

VALIDATION_PROMPT = """You are a data validation expert. Review the extracted invoice JSON and identify any inconsistencies or impossible values.

Check for:
1. Arithmetic errors (net_total + tax_total should equal total_amount, within rounding)
2. Invalid dates
3. Missing critical fields (invoice_date, invoice_number, customer_name, total_amount)
4. Unrealistic values (negative amounts, exchange rates outside 0.5-10 range, etc.)

Respond ONLY with JSON in this format:
{
  "is_valid": true/false,
  "errors": ["error 1", "error 2"],
  "warnings": ["warning 1", "warning 2"],
  "corrected_fields": {"field_name": corrected_value}
}

Data to validate:
{extracted_json}"""

# Prompt para consolidación con el script Python existente
CONSOLIDATION_PROMPT = """Given the extracted invoice data below, prepare it for consolidation into an Argentine tax authority (AFIP) format spreadsheet.

Ensure:
1. All amounts are in ARS (if in other currency, they should have been converted using the exchange_rate)
2. Dates are in YYYY-MM-DD format
3. All tax codes match AFIP standards (021=Factura A, 022=Factura B, etc.)
4. Line items have clear mapping (description, qty, price, net, IVA, total)

Invoice data:
{invoice_json}

Respond ONLY with JSON confirming readiness for consolidation:
{
  "ready_for_consolidation": true/false,
  "currency_converted": true/false,
  "consolidated_format": {extracted_invoice_in_consolidation_format}
}"""

# Ejemplo de salida esperada (para testing)
EXAMPLE_EXTRACTED_OUTPUT = {
    "invoice_date": "2025-07-15",
    "invoice_number": "00003396",
    "invoice_type": "FACTURA",
    "point_of_sale": "0004",
    "customer_name": "BASF ARGENTINA SA",
    "customer_tax_id": "30714120421",
    "currency": "ARS",
    "exchange_rate": 1.0,
    "line_items": [
        {
            "description": "Componente electrónico modelo X",
            "quantity": 2,
            "unit_price": 5000.0,
            "net_amount": 10000.0,
            "tax_amount": 2100.0,
            "total": 12100.0
        }
    ],
    "net_total": 10000.0,
    "tax_total": 2100.0,
    "total_amount": 12100.0,
    "authorization_code": "76123456789012",
    "notes": None
}

def get_extraction_prompt(invoice_text):
    """Devuelve el prompt con el texto de la factura interpolado."""
    return INVOICE_EXTRACTION_PROMPT.format(invoice_text=invoice_text)

def get_validation_prompt(extracted_json):
    """Devuelve el prompt de validación con los datos extraídos."""
    import json
    json_str = json.dumps(extracted_json, indent=2, ensure_ascii=False)
    return VALIDATION_PROMPT.format(extracted_json=json_str)

def get_consolidation_prompt(invoice_json):
    """Devuelve el prompt de consolidación."""
    import json
    json_str = json.dumps(invoice_json, indent=2, ensure_ascii=False)
    return CONSOLIDATION_PROMPT.format(invoice_json=json_str)
