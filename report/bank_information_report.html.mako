<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1 plus MathML 2.0//EN" "http://www.w3.org/Math/DTD/mathml2/xhtml-math11-f.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Liste et informations sur le personnel</title>
        <style type="text/css">
            @page {}
            table {
                border-collapse:collapse;
                border-spacing:0;
                empty-cells:show;
                border-width: 1px;
                border-style:solid;
                border-color:#000000;
            }
            th {
                font-weight: bold;
                text-align:center;
                vertical-align: middle;
                border-width: 1px;
                border-style:solid;
                border-color:#000000;
            }
            td {
                text-align: left;
                padding: 2mm;
                border-width: 1px;
                border-style:solid;
                border-color:#000000;
                font-size: 8pt;
                vertical-align: top;
            }
            h1, h2: {
                text-align: center;
            }
            .numeric {
                text-align: right;
            }
        </style>
    </head>
    <body style="text-align: center;">
        <h1>LOME CONTAINER TERMINAL</h1>
        <h2>Liste et informations sur le personnel</h2>
        <table>
            <tr>
                <th style="width: 1cm;">N°</th>
                <th style="width: 6.5cm;">Nom &amp; Prénoms</th>
                <th style="width: 6cm;">Banque</th>
                <th style="width: 2.5cm;">N° Compte à créditer</th>
                <th style="width: 2.5cm;">Montant<br/>(FCFA)</th>
            </tr>
            %for idx, payslip in enumerate(context.get('payslips'), 1):
            <tr>
                <td class="numeric">${idx}</td>
                <td>${payslip.employee_id.name}</td>
                <td>${payslip.employee_id.bank_name}</td>
                <td class="numeric">${payslip.employee_id.acc_number}</td>
                <td class="numeric">${'{0:,.0f}'.format(context.get('payslips').get(payslip).get('net_salary')).replace(',', '.')}</td>
            </tr>
            %endfor
            <tr>
                <td colspan="4" style="text-align: center;">Montant Total à virer</td>
                <td class="numeric">${'{0:,.0f}'.format(context.get('total_net')).replace(',', '.')}</td>
            </tr>
        </table>
    </body>
</html>
