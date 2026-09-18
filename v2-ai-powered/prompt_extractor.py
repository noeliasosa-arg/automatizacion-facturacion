"""
prompt_extractor.py

Módulo que encapsula la lógica de extracción de datos de facturas usando Claude.
Recibe un PDF/texto de factura y devuelve datos estructurados en JSON.
"""

import json
import os
from typing import Optional, Dict, Any
import anthropic
from prompt_extractor_config import (
    get_extraction_prompt,
    get_validation_prompt,
    get_consolidation_prompt,
)


class InvoiceExtractor:
    """Extrae datos de facturas usando Claude con prompts estructurados."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el extractor.

        Args:
            api_key: Clave de Anthropic. Si no se proporciona, usa ANTHROPIC_API_KEY.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY no está configurada. "
                "Establécela como variable de entorno."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-opus-4-1"  # o claude-sonnet-4 para más velocidad

    def extract_from_text(self, invoice_text: str) -> Dict[str, Any]:
        """
        Extrae datos de un texto de factura (ej: OCR de PDF).

        Args:
            invoice_text: Texto de la factura (output de OCR o texto estructurado).

        Returns:
            Dict con los datos extraídos.
        """
        prompt = get_extraction_prompt(invoice_text)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text.strip()

            # Claude debería devolver solo JSON, pero validamos
            extracted = json.loads(response_text)
            return extracted

        except json.JSONDecodeError as e:
            print(f"[ERROR] No se pudo parsear el JSON de Claude: {e}")
            print(f"Respuesta: {response_text}")
            return None
        except anthropic.APIError as e:
            print(f"[ERROR] Error en API de Claude: {e}")
            return None

    def validate_extraction(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos extraídos usando Claude.

        Args:
            extracted_data: Datos extraídos (JSON).

        Returns:
            Dict con validación: {is_valid, errors, warnings, corrected_fields}.
        """
        prompt = get_validation_prompt(extracted_data)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text.strip()
            validation = json.loads(response_text)
            return validation

        except json.JSONDecodeError as e:
            print(f"[ERROR] No se pudo parsear validación: {e}")
            return {
                "is_valid": False,
                "errors": ["Validación falló al parsear respuesta"],
                "warnings": [],
                "corrected_fields": {},
            }
        except anthropic.APIError as e:
            print(f"[ERROR] Error en validación de Claude: {e}")
            return {
                "is_valid": False,
                "errors": [f"Error API: {str(e)}"],
                "warnings": [],
                "corrected_fields": {},
            }

    def apply_corrections(
        self, extracted_data: Dict[str, Any], corrections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Aplica correcciones sugeridas por la validación.

        Args:
            extracted_data: Datos originales.
            corrections: Campo "corrected_fields" de la validación.

        Returns:
            Datos corregidos.
        """
        corrected = extracted_data.copy()
        if corrections:
            corrected.update(corrections)
        return corrected

    def prepare_for_consolidation(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara los datos para consolidación en la planilla AFIP.

        Args:
            validated_data: Datos validados y corregidos.

        Returns:
            Datos en formato listo para consolidación.
        """
        prompt = get_consolidation_prompt(validated_data)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text.strip()
            consolidated = json.loads(response_text)
            return consolidated

        except json.JSONDecodeError as e:
            print(f"[ERROR] No se pudo parsear consolidación: {e}")
            # Fallback: devolvemos los datos originales sin formato especial
            return {"ready_for_consolidation": False, "consolidated_format": validated_data}

    def extract_validate_prepare(self, invoice_text: str) -> Dict[str, Any]:
        """
        Pipeline completo: extrae → valida → corrige → prepara.

        Args:
            invoice_text: Texto de factura.

        Returns:
            Dict con resultado final {success, extracted, validation, consolidated}.
        """
        print("[INFO] Extrayendo datos...")
        extracted = self.extract_from_text(invoice_text)
        if not extracted:
            return {"success": False, "error": "No se pudieron extraer datos"}

        print("[INFO] Validando...")
        validation = self.validate_extraction(extracted)

        if validation.get("corrected_fields"):
            print("[INFO] Aplicando correcciones...")
            extracted = self.apply_corrections(extracted, validation["corrected_fields"])

        print("[INFO] Preparando para consolidación...")
        consolidated = self.prepare_for_consolidation(extracted)

        return {
            "success": validation.get("is_valid", False),
            "extracted": extracted,
            "validation": validation,
            "consolidated": consolidated,
        }


# Ejemplo de uso
if __name__ == "__main__":
    # Test básico
    sample_invoice = """
    FACTURA
    Fecha: 15/07/2025
    Número: 0004-00003396
    
    Cliente: BASF ARGENTINA SA
    CUIT: 30714120421
    
    Concepto: Componente electrónico modelo X
    Cantidad: 2
    Precio unitario: $5000
    Subtotal: $10000
    IVA (21%): $2100
    Total: $12100
    
    CAE: 76123456789012
    """

    extractor = InvoiceExtractor()
    result = extractor.extract_validate_prepare(sample_invoice)

    print("\n=== RESULTADO ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
