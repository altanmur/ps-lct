<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1 plus MathML 2.0//EN" "http://www.w3.org/Math/DTD/mathml2/xhtml-math11-f.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />
        <title>Balance Des Comptes</title>
        <style type="text/css">
            th, td {vertical-align: top;}
            .totals {font-weight: bold; text-align: right;}
        </style>
    </head>
    <body dir="ltr" style="max-width:29.7cm;margin-top:0.254cm; margin-bottom:0.254cm; margin-left:0.762cm; margin-right:0.762cm; writing-mode:lr-tb; ">
        ${context}
        <table style="text-align: left; width: 100%;" border="0" cellpadding="0" cellspacing="0">
            <tr>
                <th colspan="2">
                    ${context.get('company_name')}
                </th>
                <th colspan="4" style="text-align: center;">
                    <h1>Balance des comptes</h1>
                    <b>Complète</b>
                </th>
                <th colspan="2">
                    <table style="text-align: left; width: 100%;" border="0" cellpadding="0" cellspacing="0">
                        <tr><td>Période du</td><td>${context.get('start_date')}</td></tr>
                        <tr><td>au</td><td>${context.get('end_date')}</td></tr>
                        <tr><td>Tenue de compte:</td><td>FIXME: what goes here?</td></tr>
                    </table>
                </th>
            </tr>
            <tr>
                <td colspan="8">Date de tirage ${context.get('current_date')} à ${context.get('current_time')}</td>
            </tr>
            <tr>
                <th rowspan="2">Numéro de compte</th>
                <th rowspan="2">Intitulé des comptes</th>
                <th colspan="2">Mouvements au ${context.get('prev_period_end')}</th>
                <th colspan="2">Mouvements</th>
                <th colspan="2">Soldes cummulés</th>
            </tr>
            <tr>
                <th>Débit</th>
                <th>Crédit</th>
                <th>Débit</th>
                <th>Crédit</th>
                <th>Débit</th>
                <th>Crédit</th>
            </tr>
            %for line in context.get('lines'):
            <tr>
                <td>${line.get('account_nbr')}</td>
                <td>${line.get('account_name')}</td>
                <td>${line.get('prev_debit')}</td>
                <td>${line.get('prev_credit')}</td>
                <td>${line.get('debit')}</td>
                <td>${line.get('credit')}</td>
                <td>
                    %if line.get('balance') < 0:
                    ${-1 * line.get('balance')}
                    %else:
                    <!-- -->
                    %endif
                </td>
                <td>
                    %if line.get('balance') >= 0:
                    ${line.get('balance')}
                    %else:
                    <!-- -->
                    %endif
                </td>
            </tr>
            %endfor
            <tr>
                <td colspan="2" class="totals">
                    A reporter
                </td>
                <td>${context.get('total_prev_debit')}</td>
                <td>${context.get('total_prev_credit')}</td>
                <td>${context.get('total_debit')}</td>
                <td>${context.get('total_credit')}</td>
                <td>
                    %if context.get('total_balance') < 0:
                    ${-1 * context.get('total_balance')}
                    %else:
                    <!-- -->
                    %endif
                </td>
                <td>
                    %if context.get('total_balance') >= 0:
                    ${context.get('total_balance')}
                    %else:
                    <!-- -->
                    %endif
                </td>
            </tr>
        </table>
    </body>
</html>
