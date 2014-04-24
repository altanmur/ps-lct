<html>
	<head>
		<style type="text/css">
			#title 
			{margin-left:auto;margin-right:auto;width:6em;text-decoration: underline;}
		</style>
	</head>
	
	<header>
		<h1 id="title" >Invoice</h1>
	</header>
	<body>
		<table>
			<tr>
				<td>DATE</td>
				<td>${formatLang(objects[0].date_invoice, date=True)}</td>
			</tr>
			<tr>
				<td>EXERCICE</td>
				<td>${objects[0].amount_total}</td>
			</tr>
		</table>
		
		
			
	</body>
</html>
