<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1 plus MathML 2.0//EN" "http://www.w3.org/Math/DTD/mathml2/xhtml-math11-f.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />
        <title>Virement Bancaire</title>
        <style type="text/css">
            .address {text-align: right; font-size: 8pt; font-weight: bold;}
            .head_right {text-align: right; font-size: 10pt;}
            .bold {font-weight: bold;}
            .ul {text-decoration: underline;}
            h1 {text-decoration: underline; color: #999999;}
        </style>
    </head>
    <body dir="ltr" style="max-width:29.7cm;margin-top:0.254cm; margin-bottom:0.254cm; margin-left:0.762cm; margin-right:0.762cm; writing-mode:lr-tb; ">
        %for voucher in context.get('vouchers'):
        <h1><img style="height: 1cm; width: 3.6cm;" alt="LCT" src="data:image/png;base64,${company.logo}"/>Lomé Container Terminal S.A.</h1>
        <div class="address">
            NIF: 090164W<br/>
            RCCM/: Lomé 2008 B 2184<br/>
            09BP9103 Lomé - TOGO<br/>
            Tel: (+228) 22 23 76 76/80<br/>
            Fax: (+228) 22 23 76 79<br/><br/>
        </div>
        <div class="head_right">
            Lomé, ${voucher.date}<br/>
            <br/>
            <span class="bold">
                DIAMOND BANK<br/><br/>
                3519, Boulevard du 13 janvier<br/>
                BP: 3925 Doulassamé<br/>
                <span class="ul">Lomé - Togo</span><br/>
            </span>
        </div>
        <br/>
        <span class="bold">N/Réf:</span> ${voucher.reference}<br/>
        <span style="text-decoration: underline; font-weight: bold;">Objet:</span> Ordre de virement<br/>
        <br/>
        Messieurs,<br/>
        <br/>
        Par le débit de notre compte <span class="bold">N° ${voucher.origin_bank_id.acc_number}</span> dans vos livres, nous vous remercions de transférer la somme de <span class="bold">${voucher.currency_id.name} ${voucher.amount}</span> (${context.get('vouchers').get(voucher).get('amount_text')})
        %if voucher.internal_transfer and context.get('vouchers').get(voucher).get('diff_currencies'):
        équivalent à F {context.get('vouchers').get(voucher).get('default_currency') ${context.get('vouchers').get(voucher).get('amount_default')} (${context.get('vouchers').get(voucher).get('amount_text_default')}) vers notre compte {context.get('vouchers').get(voucher).get('default_currency') ouvert dans vos livres aux références suivantes:
        %else:
        vers le compte aux références suivantes:
        %endif
        <br/><br/>
        %if voucher.internal_transfer:
            <% detail = voucher.destination_bank_id %>
        %else:
            <% detail = voucher.get_invoice() %>
        %endif
        <table style="text-align: left; width: 100%;" border="0" cellpadding="0" cellspacing="0">
            <tbody>
                <tr>
                    <td style="vertical-align: top; width: 300px;"><span class="bold">Bénéficiaire:</span><br/></td>
                    <td style="vertical-align: top;">${voucher.partner_id.name}<br/></td>
                </tr>

                %if not voucher.internal_transfer:
                <tr>
                    <td style="vertical-align: top;"><span class="bold">Banque:</span><br/></td>
                    <td style="vertical-align: top;">${voucher.get_invoice().bank}<br/></td>
                </tr>
                <tr>
                    <td style="vertical-align: top;"><span class="bold">IBAN:</span><br/></td>
                    <td style="vertical-align: top;">${voucher.get_invoice().iban}</td>
                </tr>
                %endif

                <tr>
                    <td style="vertical-align: top;"><span class="bold">BIC/Swift:</span><br/></td>
                    <td style="vertical-align: top;">${detail.bank_bic}</td>
                </tr>
                <tr>
                    <td style="vertical-align: top;"><span class="bold">Code Banque:</span><br/></td>
                    <td style="vertical-align: top;">${detail.bank_code}</td>
                </tr>
                <tr>
                    <td style="vertical-align: top;"><span class="bold">Code Guichet:</span><br/></td>
                    <td style="vertical-align: top;">${detail.counter_code}</td>
                </tr>
                <tr>
                    <td style="vertical-align: top;"><span class="bold">Numéro compte:</span><br/></td>
                    <td style="vertical-align: top;">${detail.acc_number}</td>
                </tr>
                <tr>
                    <td style="vertical-align: top;"><span class="bold">RIB:</span><br/></td>
                    <td style="vertical-align: top;">${detail.rib}</td>
                </tr>
                <tr>
                    <td style="vertical-align: top;"><span class="bold">Motif:</span><br/></td>
                    <td style="vertical-align: top;">${voucher.name}</td>
                </tr>

                %if not voucher.internal_transfer:
                <tr>
                    <td style="vertical-align: top;"><span class="bold">Numéro Client:</span><br/></td>
                    <td style="vertical-align: top;">${voucher.get_invoice().customer_nbr}</td>
                </tr>
                %endif
            </tbody>
        </table>
        <br/>
        Vous souhaitant bonne réception et, restant à votre disposition pour
        tous renseignements complémentaires. Recevez, Messieurs, nos
        salutations distinguées.<br/>
        <br/>
        <br/>
        Signatures autorisées<br/>
        <br/>
        <table style="text-align: left; width: 100%;" border="0" cellpadding="0" cellspacing="0">
            <tbody>
                <tr style="vertical-align: top; height: 150px;">
                    <td>${voucher.pos1_id.name}<br/></td>
                    <td>${voucher.pos2_id.name}<br/></td>
                </tr>
                <tr>
                    <td>${voucher.signee1_id.name}<br/></td>
                    <td>${voucher.signee2_id.name}<br/></td>
                </tr>
            </tbody>
        </table>
        <br/>
        %endfor

    </body>
</html>
