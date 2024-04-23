# AWS -> Pex billing automation

This repo automates uploading AWS invoices to [Pex](https://www.pexcard.com/).

In an utterly inexcusable turn of events, AWS simply does not provide an API to download invoices with. Therefore to do its job the code in this repo:

1. Connects to an IMAP inbox
2. Searches for unread invoice emails from AWS
3. Retrieves their first attachment and does some sanity checking
4. Uploads this attachment to Pex
5. Waits for Pex to mark the attachment as connected to a transaction (or not)
6. Marks the email as read to indicate it's been processed

If the script crashes, the email will be left unread so that you can go fix the script and try again.

If the attachment was successfully uploaded to Pex, but Pex couldn't match it with a transaction, the script will print a warning and exit with a non-zero exit status. However it will _not_ immediately bail out, and it will still mark the email as read. The idea being that _we're_ not in the wrong, Pex is, so there's no point in stopping (and there's no point in keeping the email unread because there's nothing we can do to improve the situation). The purpose of the non-zero exit code is so your automation will blow up and you can go read the warning, then log in and fix the problem in the Pex dashboard.

## Setup

You'll need to configure AWS to email invoices to some email address accessible via IMAP. You'll also need to define these environment variables:

* `IMAP_HOST`
* `IMAP_USERNAME`
* `IMAP_PASSWORD`
* `PEX_BEARER_TOKEN` - good luck with this one. I copied it from Developer Tools but it expires so have fun getting it in a sane way. Ideally this script would log in and use the IMAP credentials to MFA. Or we could ask Pex for an actual long-lived API token.

## Author

AJ Jordan <aj@seagl.org>

## License

AGPL 3.0 or later
