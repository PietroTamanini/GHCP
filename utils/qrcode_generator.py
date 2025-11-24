import qrcode
import io
import base64
from config import Config

def gerar_qrcode_pix(valor_total):
    """Gera QR Code e código Copia e Cola PIX com base no valor total"""
    
    def emv(id, valor):
        tamanho = str(len(valor)).zfill(2)
        return f"{id}{tamanho}{valor}"

    merchant_account = emv("00", "br.gov.bcb.pix") + emv("01", Config.PIX_CHAVE)
    merchant_info = emv("26", merchant_account)
    transaction_amount = emv("54", f"{valor_total:.2f}")
    txid = emv("05", f"GHCP{int(valor_total * 100)}")

    payload = (
        emv("00", "01")
        + emv("01", "12")
        + merchant_info
        + emv("52", "0000")
        + emv("53", "986")
        + transaction_amount
        + emv("58", "BR")
        + emv("59", Config.PIX_NOME)
        + emv("60", Config.PIX_CIDADE)
        + emv("62", txid)
    )

    def crc16(payload):
        polinomio = 0x1021
        resultado = 0xFFFF
        payload += "6304"
        for byte in bytearray(payload, "utf-8"):
            resultado ^= byte << 8
            for _ in range(8):
                if resultado & 0x8000:
                    resultado = (resultado << 1) ^ polinomio
                else:
                    resultado <<= 1
                resultado &= 0xFFFF
        return f"{payload}{resultado:04X}"

    copia_cola = crc16(payload)

    img = qrcode.make(copia_cola)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return qr_base64, copia_cola