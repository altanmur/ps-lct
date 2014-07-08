<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1 plus MathML 2.0//EN" "http://www.w3.org/Math/DTD/mathml2/xhtml-math11-f.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />
        <title>Balance Des Comptes</title>
        <style type="text/css">
            th, td {vertical-align: top;}
            .totals {font-weight: bold; text-align: right;}
            .acc_type_view {font-weight:bold;}
            .numeric {text-align: right;}
        </style>
    </head>
    <body dir="ltr" style="max-width:29.7cm;margin-top:0.254cm; margin-bottom:0.254cm; margin-left:0.762cm; margin-right:0.762cm; writing-mode:lr-tb; ">
        ${context}
        <table style="text-align: left; width: 100%;" border="0" cellpadding="5px;" cellspacing="0">
            <tr>
                <th colspan="5">
                    ${context.get('company_name')}
                </th>
                <th colspan="3">
                    <table style="text-align: left; width: 100%;" border="0" cellpadding="0" cellspacing="0">
                        <tr><td>Période du</td><td>${context.get('start_date')}</td></tr>
                        <tr><td>au</td><td>${context.get('end_date')}</td></tr>
                        <tr><td colspan="2">&nbsp;</td></tr>
                    </table>
                </th>
            </tr>
            <tr>
                <th colspan="8" style="text-align: center;">
                    <h1>Balance des comptes</h1>
                    <b>${context.get('display_account')}</b>
                </th>
            </tr>
            <tr>
                <td colspan="8">Date de tirage: ${context.get('current_date')} à ${context.get('current_time')}</td>
            </tr>
            <tr style="text-align: center;">
                <th rowspan="2">Numéro de compte</th>
                <th rowspan="2">Intitulé des comptes</th>
                <th colspan="2">Mouvements au ${context.get('prev_period_end')}</th>
                <th colspan="2">Mouvements</th>
                <th colspan="2">Soldes cummulés</th>
            </tr>
            <tr style="text-align: center;">
                <th>Débit</th>
                <th>Crédit</th>
                <th>Débit</th>
                <th>Crédit</th>
                <th>Débit</th>
                <th>Crédit</th>
            </tr>
            %for line in context.get('lines'):
            %if line.get('type') == 'view':
            <tr class="acc_type_view">
            %else:
            <tr>
            %endif
                <td>${line.get('code')}</td>
                <td>${line.get('name')}</td>
                <td class="numeric">
                    ${'{0:,.0f}'.format(line.get('prev_debit')).replace(',', '.')}
                </td>
                <td class="numeric">
                    ${'{0:,.0f}'.format((abs(line.get('prev_credit')))).replace(',', '.')}
                </td>
                <td class="numeric">
                    ${'{0:,.0f}'.format(line.get('debit')).replace(',', '.')}
                </td>
                <td class="numeric">
                    ${'{0:,.0f}'.format(line.get('credit')).replace(',', '.')}
                </td>
                <td class="numeric">
                    %if line.get('balance') > 0:
                    ${'{0:,.0f}'.format(line.get('balance')).replace(',', '.')}
                    %else:
                    <!-- -->
                    %endif
                </td>
                <td class="numeric">
                    %if line.get('balance') <= 0:
                    ${'{0:,.0f}'.format((abs(line.get('balance')))).replace(',', '.')}
                    %else:
                    <!-- -->
                    %endif
                </td>
            </tr>
            %endfor
            <tr class="totals">
                <td colspan="2">
                    A reporter
                </td>
                <td class="numeric">${'{0:,.0f}'.format(context.get('total_prev_debit')).replace(',', '.')}</td>
                <td class="numeric">${'{0:,.0f}'.format(context.get('total_prev_credit')).replace(',', '.')}</td>
                <td class="numeric">${'{0:,.0f}'.format(context.get('total_debit')).replace(',', '.')}</td>
                <td class="numeric">${'{0:,.0f}'.format(context.get('total_credit')).replace(',', '.')}</td>
                <td class="numeric">
                    %if context.get('total_balance') > 0:
                    ${'{0:,.0f}'.format(context.get('total_balance')).replace(',', '.')}
                    %else:
                    <!-- -->
                    %endif
                </td>
                <td class="numeric">
                    %if context.get('total_balance') <= 0:
                    ${'{0:,.0f}'.format(abs(context.get('total_balance'))).replace(',', '.')}
                    %else:
                    <!-- -->
                    %endif
                </td>
            </tr>
        </table>
    </body>
</html>
