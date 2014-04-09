<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1 plus MathML 2.0//EN" "http://www.w3.org/Math/DTD/mathml2/xhtml-math11-f.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Liste et informations sur le personnel</title>
        <style type="text/css">
            @page {}
            table { border-collapse:collapse; border-spacing:0; empty-cells:show; border-width: 1px; border-style:solid; border-color:#000000;}
            th {font-weight: bold; text-align:center; vertical-align: middle; border-width: 1px; border-style:solid; border-color:#000000;}
            td {text-align: left; padding: 2mm; border-width: 1px; border-style:solid; border-color:#000000;}
            h1, h2: {text-align: center;}
            .numeric {text-align: right;}
        </style>
    </head>
    <body style="text-align: center;">
        <h1>LOME CONTAINER TERMINAL</h1>
        <h2>Liste et informations sur le personnel</h2>
        <table>
            <tr>
                <th style="width: 1cm;">N°</th>
                <th style="width: 5cm;">Nom &amp; Prénoms</th>
                <th style="width: 5cm;">Banque</th>
                <th style="width: 5cm;">N° Compte à créditer</th>
                <th style="width: 2.5cm;">Montant<br/>(FCFA)</th>
            </tr>
            %for idx, payslip in enumerate(context.get('payslips'), 1):
            <tr>
                <td class="numeric">${idx}</td>
                <td>${payslip.employee_id.name}</td>
                <td>${payslip.employee_id.bank_name}</td>
                <td>${payslip.employee_id.acc_number}</td>
                <td class="numeric">${int(context.get('payslips').get(payslip).get('net_salary'))}</td>
            </tr>
            %endfor
            <tr>
                <td colspan="4" style="text-align: center;">Montant Total à virer</td>
                <td class="numeric">${int(context.get('total_net'))}</td>
            </tr>
        </table>
    </body>
</html>
