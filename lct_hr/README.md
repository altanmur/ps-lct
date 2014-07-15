openerp_hr_togo
===============

Important!

For the PDF reports, use wkhtmltopdf v0.10 or 0.11:
* v0.9 doesn't do page breaks, not even when forced through CSS
* V0.12 insists on putting a page break after every table row and exits with error code 1 because for some reason it tries to interpret path names as URLs, prepends 'http://' and then acts surprised when 'http://tmp/xyz.html' is not actually retrievable over the Internet. If this happens, just write a wrapper shell script that follows the call to wkhtmltopdf with an exit 0, and configure the path to the webkit report to use the wrapper instead.
